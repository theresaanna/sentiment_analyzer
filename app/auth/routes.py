from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import bp
from app import db
from app.models import User
from authlib.integrations.flask_client import OAuth
import stripe
import os

# Initialize OAuth container (lazy)
oauth = OAuth()

def _get_google_client():
    oauth.init_app(current_app)
    if 'google' not in getattr(oauth, '_clients', {}):
        client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
        if not client_id or not client_secret:
            current_app.logger.error('Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.')
        oauth.register(
            name='google',
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            api_base_url='https://openidconnect.googleapis.com/v1/',
            client_kwargs={'scope': 'openid email profile'}
        )
    return oauth.create_client('google')

@bp.route('/google/callback')
def google_callback():
    google = _get_google_client()
    try:
        token = google.authorize_access_token()
        resp = google.get('userinfo')
        userinfo = resp.json() if resp else None
    except Exception as e:
        current_app.logger.error(f'Google OAuth callback error: {e}')
        flash('Failed to authenticate with Google.', 'danger')
        return redirect(url_for('main.index'))

    if not userinfo or not userinfo.get('email'):
        flash('Google did not provide an email address.', 'danger')
        return redirect(url_for('main.index'))

    email = userinfo['email'].lower()
    name = userinfo.get('name') or email.split('@')[0]

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(name=name, email=email, provider='google')
        user.set_password(os.urandom(16).hex())
        db.session.add(user)
        db.session.commit()
    else:
        updated = False
        if user.name != name and name:
            user.name = name
            updated = True
        if user.provider != 'google':
            user.provider = 'google'
            updated = True
        if updated:
            db.session.commit()

    login_user(user)
    flash('Logged in with Google.', 'success')

    next_url = request.args.get('next')
    return redirect(next_url or url_for('main.index'))


@bp.before_app_request
def configure_stripe_and_context():
    # Configure Stripe API key for the request context
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')


@bp.route('/__disabled_register', methods=['GET', 'POST'])
def register():
    flash('Registration is no longer required. Please sign in with Google.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    google = _get_google_client()
    redirect_uri = current_app.config.get('OAUTH_REDIRECT_URI') or url_for('auth.google_callback', _external=True)
    next_url = request.args.get('next')
    if next_url:
        redirect_uri = url_for('auth.google_callback', _external=True, next=next_url)
    try:
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        current_app.logger.error(f'Google authorize redirect failed: {e}')
        flash('Authentication is temporarily unavailable. Please try again later.', 'danger')
        return redirect(url_for('main.index'))


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@bp.route('/__disabled_reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    flash('Password reset is not available. Please sign in with Google.', 'info')
    return redirect(url_for('auth.login'))


# Debug endpoints removed for clean deployment


@bp.route('/__disabled_reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    flash('Password reset is not available. Please sign in with Google.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')


@bp.route('/subscribe')
@login_required
def subscribe():
    return render_template('auth/subscribe.html',
                           stripe_price_id=current_app.config.get('STRIPE_PRICE_ID'))


@bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    price_id = current_app.config.get('STRIPE_PRICE_ID')
    if not price_id:
        return jsonify({'error': 'Stripe price is not configured'}), 400

    domain = request.host_url.rstrip('/')
    success_url = url_for('auth.subscribe_success', _external=True)
    cancel_url = url_for('auth.subscribe', _external=True)

    try:
        session = stripe.checkout.Session.create(
            mode='subscription',
            line_items=[{'price': price_id, 'quantity': 1}],
            success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=cancel_url,
            customer_email=current_user.email,
            metadata={'user_id': current_user.id}
        )
        return jsonify({'url': session.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/subscribe/success')
@login_required
def subscribe_success():
    # Mark user as subscribed optimistically. For production, verify via webhooks.
    if not current_user.is_subscribed:
        current_user.is_subscribed = True
        current_user.provider = 'stripe'
        db.session.commit()
    flash('Subscription activated! Enjoy your full access.', 'success')
    return redirect(url_for('auth.profile'))


@bp.route('/stripe/webhook', methods=['POST', 'GET', 'HEAD'])
def stripe_webhook():
    # Health check for GET/HEAD to verify deployment and routing
    if request.method != 'POST':
        return jsonify({'status': 'ok'}), 200

    # Verify the webhook signature for POST
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
    if not webhook_secret:
        return jsonify({'error': 'Webhook secret not configured'}), 500

    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig_header, secret=webhook_secret
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400

    event_type = event.get('type')
    data_object = event.get('data', {}).get('object', {})

    # Handle checkout completion (initial activation)
    if event_type == 'checkout.session.completed':
        mode = data_object.get('mode')
        if mode == 'subscription':
            metadata = data_object.get('metadata') or {}
            user_id = metadata.get('user_id')
            if user_id:
                try:
                    user = User.query.get(int(user_id))
                except Exception:
                    user = None
                if user:
                    user.is_subscribed = True
                    user.provider = 'stripe'
                    user.customer_id = data_object.get('customer')
                    db.session.commit()

    # Handle subscription lifecycle updates
    elif event_type in ('customer.subscription.updated', 'customer.subscription.deleted'):
        customer_id = data_object.get('customer')
        status = data_object.get('status')
        if customer_id:
            user = User.query.filter_by(customer_id=customer_id).first()
            if user:
                active_statuses = ('trialing', 'active', 'past_due')
                user.is_subscribed = status in active_statuses
                user.provider = 'stripe'
                db.session.commit()

    # Handle payment failures (optional: immediately mark inactive)
    elif event_type == 'invoice.payment_failed':
        customer_id = data_object.get('customer')
        if customer_id:
            user = User.query.filter_by(customer_id=customer_id).first()
            if user:
                user.is_subscribed = False
                db.session.commit()

    return jsonify({'received': True})



from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import bp
from app import db
from app.models import User
from app.auth.forms import RegisterForm, LoginForm, PasswordResetRequestForm, PasswordResetForm
from app.email import send_password_reset_email
import stripe


@bp.before_app_request
def configure_stripe_and_context():
    # Configure Stripe API key for the request context
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegisterForm()
    if form.validate_on_submit():
        # Create user
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('Email already registered. Please login instead.', 'warning')
            return redirect(url_for('auth.login'))
        user = User(name=form.name.data.strip(), email=form.email.data.lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Account created. Please choose a subscription to continue.', 'success')
        return redirect(url_for('auth.subscribe'))
    return render_template('auth/register.html', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            try:
                send_password_reset_email(user)
                flash('Check your email for instructions to reset your password.', 'info')
            except Exception as e:
                current_app.logger.error(f'Failed to send password reset email: {str(e)}')
                flash('Failed to send password reset email. Please check that email is configured.', 'danger')
        else:
            # Don't reveal if the email exists or not for security
            flash('Check your email for instructions to reset your password.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        flash('Invalid or expired password reset link.', 'danger')
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset. You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


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



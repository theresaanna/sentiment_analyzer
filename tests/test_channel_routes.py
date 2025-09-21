"""Tests for channel management routes."""
import json
import pytest
from app import db
from app.models import User, Channel, UserChannel


def test_add_channel_requires_pro(client, auth_client):
    """Test that adding a channel requires pro subscription."""
    # Try to add channel as free user
    response = auth_client.post('/api/channel/add', 
                                json={'channel_url': '@testchannel'})
    assert response.status_code == 403
    data = json.loads(response.data)
    assert not data['success']
    assert 'Pro subscription required' in data['error']


def test_add_channel_success(pro_client, app):
    """Test successful channel addition for pro user."""
    with app.app_context():
        # Add a channel
        response = pro_client.post('/api/channel/add',
                                  json={'channel_url': '@testchannel'})
        
        # Should succeed (with placeholder data for now)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'channel' in data
        assert data['channel']['handle'] == '@testchannel'


def test_add_duplicate_channel(pro_client, app):
    """Test that duplicate channels cannot be added."""
    with app.app_context():
        # Create a channel first
        channel = Channel(
            yt_channel_id='UCtest123',
            title='Test Channel',
            handle='@testchannel'
        )
        db.session.add(channel)
        
        # Add to user's channels
        user = User.query.filter_by(email='pro@example.com').first()
        user_channel = UserChannel(user_id=user.id, channel_id=channel.id)
        db.session.add(user_channel)
        db.session.commit()
        
        # Try to add the same channel again
        response = pro_client.post('/api/channel/add',
                                  json={'channel_url': '@testchannel'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert not data['success']
        assert 'already added' in data['error'].lower()


def test_list_channels(pro_client, app):
    """Test listing user's channels."""
    with app.app_context():
        # Create some channels
        user = User.query.filter_by(email='pro@example.com').first()
        
        for i in range(3):
            channel = Channel(
                yt_channel_id=f'UCtest{i}',
                title=f'Test Channel {i}',
                handle=f'@testchannel{i}'
            )
            db.session.add(channel)
            db.session.flush()
            
            user_channel = UserChannel(user_id=user.id, channel_id=channel.id)
            db.session.add(user_channel)
        
        db.session.commit()
        
        # List channels
        response = pro_client.get('/api/channel/list')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['count'] == 3
        assert len(data['channels']) == 3


def test_delete_channel(pro_client, app):
    """Test removing a channel from user's list."""
    with app.app_context():
        # Create a channel
        user = User.query.filter_by(email='pro@example.com').first()
        channel = Channel(
            yt_channel_id='UCtest_delete',
            title='Channel to Delete',
            handle='@deleteme'
        )
        db.session.add(channel)
        db.session.flush()
        
        user_channel = UserChannel(user_id=user.id, channel_id=channel.id)
        db.session.add(user_channel)
        db.session.commit()
        
        # Delete the channel
        response = pro_client.delete('/api/channel/UCtest_delete/delete')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        
        # Verify it's deleted
        deleted_user_channel = UserChannel.query.filter_by(
            user_id=user.id,
            channel_id=channel.id
        ).first()
        assert deleted_user_channel is None
        
        # Channel should also be deleted if no other users have it
        deleted_channel = Channel.query.filter_by(
            yt_channel_id='UCtest_delete'
        ).first()
        assert deleted_channel is None


def test_delete_nonexistent_channel(pro_client):
    """Test deleting a channel that doesn't exist."""
    response = pro_client.delete('/api/channel/UCnonexistent/delete')
    assert response.status_code == 404
    
    data = json.loads(response.data)
    assert not data['success']
    assert 'not found' in data['error'].lower()


def test_channel_url_extraction():
    """Test channel URL pattern extraction."""
    from app.main.channel_routes import extract_channel_info
    
    # Test @handle
    assert extract_channel_info('@testchannel') == {'handle': '@testchannel'}
    
    # Test YouTube URL with @
    assert extract_channel_info('https://youtube.com/@testchannel') == {'handle': '@testchannel'}
    
    # Test channel ID URL
    assert extract_channel_info('https://youtube.com/channel/UCtest123') == {'channel_id': 'UCtest123'}
    
    # Test user URL
    assert extract_channel_info('https://youtube.com/user/testuser') == {'handle': '@testuser'}
    
    # Test c/ URL
    assert extract_channel_info('https://youtube.com/c/testchannel') == {'handle': '@testchannel'}
    
    # Test plain text (assume handle)
    assert extract_channel_info('testchannel') == {'handle': '@testchannel'}
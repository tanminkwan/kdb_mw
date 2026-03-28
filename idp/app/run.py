import os
from datetime import datetime
from app import create_app

app = create_app()

def init_idp(app):
    with app.app_context():
        # Setup OAuth Client
        from app.models import db, OAuth2Client
        client_id = os.getenv('IDP_DEFAULT_CLIENT_ID', 'mwm-client')
        client = OAuth2Client.query.filter_by(client_id=client_id).first()
        if not client:
            client = OAuth2Client(
                client_id=client_id,
                client_secret=os.getenv('IDP_DEFAULT_CLIENT_SECRET', 'mwm-secret'),
                client_name='MWM App',
                redirect_uris=os.getenv('IDP_DEFAULT_REDIRECT_URIS', 'http://localhost:8000/idp/callback'),
                grant_types='authorization_code',
                scope='openid profile email',
                created_on=datetime.utcnow()
            )
            db.session.add(client)
            db.session.commit()
            print(f"Registered default IDP client: {client_id}")
            
        # Initial user sync
        try:
            from app.repositories.user_repo import UserRepository
            from app.services.sync_service import SyncService
            user_repo = UserRepository()
            svc = SyncService(user_repo)
            for source in svc.get_sync_sources():
                svc.sync_users(source)
            print("Completed initial IDP user synchronization.")
        except Exception as e:
            print(f"Initial sync failed: {e}")

# Run initialization exactly once when app loads
init_idp(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

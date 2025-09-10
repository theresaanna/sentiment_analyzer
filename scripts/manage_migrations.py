#!/usr/bin/env python
"""
Database migration management utility.
Provides easy commands for common migration operations.
"""
import os
import sys
import subprocess
import shutil
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User


class MigrationManager:
    def __init__(self):
        self.app = create_app()
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.migrations_dir = os.path.join(self.project_root, 'migrations')
        self.env = {**os.environ, 'FLASK_APP': 'run.py'}
    
    def run_command(self, cmd):
        """Run a Flask-Migrate command."""
        result = subprocess.run(
            cmd, 
            env=self.env,
            capture_output=True, 
            text=True,
            cwd=self.project_root
        )
        return result
    
    def status(self):
        """Show current migration status."""
        print("📊 Migration Status")
        print("=" * 50)
        
        # Check if migrations folder exists
        if not os.path.exists(self.migrations_dir):
            print("❌ No migrations initialized. Run 'init' first.")
            return False
        
        # Get current migration
        result = self.run_command(['flask', 'db', 'current'])
        if result.returncode == 0:
            print("Current migration:")
            print(result.stdout)
        else:
            print("Error getting current migration:")
            print(result.stderr)
        
        # Get migration history
        result = self.run_command(['flask', 'db', 'history'])
        if result.returncode == 0:
            print("\nMigration history:")
            print(result.stdout)
        
        return True
    
    def init(self):
        """Initialize migrations."""
        if os.path.exists(self.migrations_dir):
            print(f"⚠️  Migrations already initialized at {self.migrations_dir}")
            response = input("Reinitialize? This will delete existing migrations (y/n): ")
            if response.lower() != 'y':
                return False
            
            shutil.rmtree(self.migrations_dir)
            print("Removed existing migrations.")
        
        print("Initializing migrations...")
        result = self.run_command(['flask', 'db', 'init'])
        
        if result.returncode == 0:
            print("✅ Migrations initialized successfully!")
            print(result.stdout)
            return True
        else:
            print("❌ Failed to initialize migrations:")
            print(result.stderr)
            return False
    
    def create(self, message=None):
        """Create a new migration."""
        if not os.path.exists(self.migrations_dir):
            print("❌ Migrations not initialized. Run 'init' first.")
            return False
        
        if not message:
            message = input("Enter migration message: ")
        
        print(f"Creating migration: {message}")
        cmd = ['flask', 'db', 'migrate', '-m', message]
        result = self.run_command(cmd)
        
        if result.returncode == 0:
            print("✅ Migration created successfully!")
            print(result.stdout)
            
            # Show the migration file
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Generating' in line and '.py' in line:
                    migration_file = line.split('Generating')[-1].strip().rstrip(' ... done')
                    print(f"\n📄 Migration file: {migration_file}")
                    
                    # Ask if user wants to review it
                    if input("Review migration? (y/n): ").lower() == 'y':
                        with open(migration_file, 'r') as f:
                            print("\n" + "=" * 50)
                            print(f.read())
                            print("=" * 50)
            
            return True
        else:
            print("❌ Failed to create migration:")
            print(result.stderr)
            return False
    
    def upgrade(self, revision='head'):
        """Apply migrations."""
        if not os.path.exists(self.migrations_dir):
            print("❌ Migrations not initialized. Run 'init' first.")
            return False
        
        print(f"Applying migrations (target: {revision})...")
        
        # Backup database before upgrade
        from scripts.db_backup import DatabaseBackup
        backup_manager = DatabaseBackup()
        backup_path = backup_manager.backup()
        
        if backup_path:
            print(f"✓ Database backed up to: {backup_path}")
        
        # Run upgrade
        cmd = ['flask', 'db', 'upgrade', revision]
        result = self.run_command(cmd)
        
        if result.returncode == 0:
            print("✅ Migrations applied successfully!")
            print(result.stdout)
            return True
        else:
            print("❌ Failed to apply migrations:")
            print(result.stderr)
            
            if backup_path:
                print("\n⚠️  You can restore the database using:")
                print(f"   python scripts/db_restore.py --backup {backup_path}")
            
            return False
    
    def downgrade(self, revision='-1'):
        """Rollback migrations."""
        if not os.path.exists(self.migrations_dir):
            print("❌ Migrations not initialized.")
            return False
        
        print(f"Rolling back migrations (target: {revision})...")
        
        # Backup database before downgrade
        from scripts.db_backup import DatabaseBackup
        backup_manager = DatabaseBackup()
        backup_path = backup_manager.backup()
        
        if backup_path:
            print(f"✓ Database backed up to: {backup_path}")
        
        # Run downgrade
        cmd = ['flask', 'db', 'downgrade', str(revision)]
        result = self.run_command(cmd)
        
        if result.returncode == 0:
            print("✅ Rollback successful!")
            print(result.stdout)
            return True
        else:
            print("❌ Failed to rollback:")
            print(result.stderr)
            return False
    
    def stamp(self, revision='head'):
        """Mark database as at a specific migration without running it."""
        print(f"Stamping database at revision: {revision}")
        
        cmd = ['flask', 'db', 'stamp', revision]
        result = self.run_command(cmd)
        
        if result.returncode == 0:
            print("✅ Database stamped successfully!")
            return True
        else:
            print("❌ Failed to stamp database:")
            print(result.stderr)
            return False
    
    def check_pending(self):
        """Check for pending migrations."""
        if not os.path.exists(self.migrations_dir):
            print("❌ Migrations not initialized.")
            return False
        
        # Get current revision
        result = self.run_command(['flask', 'db', 'current'])
        if result.returncode != 0:
            print("Unable to get current revision")
            return False
        
        current = result.stdout.strip()
        
        # Get head revision
        result = self.run_command(['flask', 'db', 'heads'])
        if result.returncode != 0:
            print("Unable to get head revision")
            return False
        
        head = result.stdout.strip()
        
        if current == head:
            print("✅ Database is up to date!")
            return True
        else:
            print("⚠️  There are pending migrations!")
            print(f"   Current: {current}")
            print(f"   Latest:  {head}")
            print("\nRun 'upgrade' to apply pending migrations.")
            return False
    
    def auto_migrate(self):
        """Automatically create and apply migration if there are changes."""
        print("🔄 Auto-migration check...")
        
        # Create migration
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        message = f"Auto migration {timestamp}"
        
        cmd = ['flask', 'db', 'migrate', '-m', message]
        result = self.run_command(cmd)
        
        if 'No changes in schema detected' in result.stdout:
            print("✅ No schema changes detected.")
            return True
        elif result.returncode == 0:
            print(f"✅ Migration created: {message}")
            print(result.stdout)
            
            # Apply migration
            if input("\nApply this migration now? (y/n): ").lower() == 'y':
                return self.upgrade()
            
            return True
        else:
            print("❌ Auto-migration failed:")
            print(result.stderr)
            return False


def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database migration management')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Status command
    subparsers.add_parser('status', help='Show migration status')
    
    # Init command
    subparsers.add_parser('init', help='Initialize migrations')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new migration')
    create_parser.add_argument('-m', '--message', help='Migration message')
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser('upgrade', help='Apply migrations')
    upgrade_parser.add_argument('revision', nargs='?', default='head', 
                               help='Target revision (default: head)')
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser('downgrade', help='Rollback migrations')
    downgrade_parser.add_argument('revision', nargs='?', default='-1',
                                 help='Target revision (default: -1)')
    
    # Stamp command
    stamp_parser = subparsers.add_parser('stamp', help='Mark database at revision')
    stamp_parser.add_argument('revision', nargs='?', default='head',
                             help='Target revision (default: head)')
    
    # Check command
    subparsers.add_parser('check', help='Check for pending migrations')
    
    # Auto command
    subparsers.add_parser('auto', help='Auto-create and apply migrations')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = MigrationManager()
    
    if args.command == 'status':
        manager.status()
    elif args.command == 'init':
        manager.init()
    elif args.command == 'create':
        manager.create(args.message)
    elif args.command == 'upgrade':
        manager.upgrade(args.revision)
    elif args.command == 'downgrade':
        manager.downgrade(args.revision)
    elif args.command == 'stamp':
        manager.stamp(args.revision)
    elif args.command == 'check':
        manager.check_pending()
    elif args.command == 'auto':
        manager.auto_migrate()


if __name__ == '__main__':
    main()

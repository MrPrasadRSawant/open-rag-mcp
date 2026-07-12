from alembic.config import Config

from alembic import command
from app.core.config import REPOSITORY_ROOT


def alembic_config() -> Config:
    config_path = REPOSITORY_ROOT / "backend" / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("script_location", str(REPOSITORY_ROOT / "backend" / "alembic"))
    return config


def upgrade_database(revision: str = "head") -> None:
    command.upgrade(alembic_config(), revision)


def downgrade_database(revision: str = "-1") -> None:
    command.downgrade(alembic_config(), revision)


def migration_directory():
    return REPOSITORY_ROOT / "backend" / "alembic"

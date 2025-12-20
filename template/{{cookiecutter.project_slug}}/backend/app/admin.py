{%- if cookiecutter.enable_admin_panel and cookiecutter.use_postgresql %}
"""SQLAdmin configuration."""

from typing import ClassVar

from sqlalchemy import create_engine
from sqladmin import Admin, ModelView
{%- if cookiecutter.admin_require_auth %}
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
{%- endif %}

from app.core.config import settings
from app.db.models.user import User
{%- if cookiecutter.admin_require_auth %}
from app.core.security import verify_password
{%- endif %}

# SQLAdmin requires a synchronous engine
sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=settings.DEBUG)

{%- if cookiecutter.admin_require_auth %}


class AdminAuth(AuthenticationBackend):
    """Admin panel authentication backend.

    Requires superuser credentials to access the admin panel.
    """

    async def login(self, request: Request) -> bool:
        """Validate admin login credentials."""
        form = await request.form()
        email = form.get("username")
        password = form.get("password")

        if not email or not password:
            return False

        # Get user from database
        from sqlalchemy.orm import Session
        with Session(sync_engine) as session:
            user = session.query(User).filter(User.email == email).first()

            if (
                user
                and verify_password(str(password), user.hashed_password)
                and user.is_superuser
            ):
                # Store user info in session
                request.session["admin_user_id"] = str(user.id)
                request.session["admin_email"] = user.email
                return True

        return False

    async def logout(self, request: Request) -> bool:
        """Clear admin session."""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Check if user is authenticated."""
        admin_user_id = request.session.get("admin_user_id")
        if not admin_user_id:
            return False

        # Verify user still exists and is superuser
        from sqlalchemy.orm import Session
        with Session(sync_engine) as session:
            user = session.query(User).filter(User.id == admin_user_id).first()
            if user and user.is_superuser and user.is_active:
                return True

        # User no longer valid, clear session
        request.session.clear()
        return False
{%- endif %}


class UserAdmin(ModelView, model=User):  # type: ignore[call-arg]
    """User admin view."""

    column_list: ClassVar = [User.id, User.email, User.is_active, User.is_superuser, User.created_at]
    column_searchable_list: ClassVar = [User.email, User.full_name]
    column_sortable_list: ClassVar = [User.id, User.email, User.is_active, User.created_at]
    form_excluded_columns: ClassVar = [User.hashed_password, User.created_at, User.updated_at]
    can_create: ClassVar = True
    can_edit: ClassVar = True
    can_delete: ClassVar = True
    can_view_details: ClassVar = True


def setup_admin(app):
    """Setup SQLAdmin for the FastAPI app."""
    {%- if cookiecutter.admin_require_auth %}
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    admin = Admin(
        app,
        sync_engine,
        title="{{ cookiecutter.project_name }} Admin",
        authentication_backend=authentication_backend,
    )
    {%- else %}
    admin = Admin(
        app,
        sync_engine,
        title="{{ cookiecutter.project_name }} Admin",
    )
    {%- endif %}
    admin.add_view(UserAdmin)
    return admin
{%- else %}
"""Admin panel - not configured."""
{%- endif %}

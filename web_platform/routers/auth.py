from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from authlib.integrations.starlette_client import OAuth
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, TEMPLATES_DIR
from database import db_cursor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)

oauth = OAuth()
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get("/login")
def login_page(request: Request):
    # Render the custom login UI
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/auth/login")
async def auth_login(request: Request):
    # Redirect to Google's consent screen
    # For localhost testing, ensure protocol is preserved or forced to http if behind proxy
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if not user_info:
            return RedirectResponse(url="/login?error=auth_failed")

        google_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name")
        picture = user_info.get("picture")

        # Upsert user into database
        with db_cursor() as cur:
            cur.execute("""
                INSERT INTO users (google_id, email, name, picture, last_login)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (google_id) DO UPDATE 
                SET email = EXCLUDED.email, 
                    name = EXCLUDED.name, 
                    picture = EXCLUDED.picture, 
                    last_login = NOW()
                RETURNING id;
            """, (google_id, email, name, picture))
            user_row = cur.fetchone()
            user_id = user_row["id"]

        # Store basic info in secure session
        request.session["user"] = {
            "id": user_id,
            "email": email,
            "name": name,
            "picture": picture
        }
        
        return RedirectResponse(url="/")
        
    except Exception as e:
        logger.error(f"OAuth Callback Error: {e}")
        return RedirectResponse(url="/login?error=callback_failed")

@router.get("/auth/logout")
async def auth_logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")

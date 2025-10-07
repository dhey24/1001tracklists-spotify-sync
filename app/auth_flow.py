# Minimal OAuth code grant to obtain a refresh token once.
import os
import webbrowser
import time
import json
import requests
from pathlib import Path
from urllib.parse import urlencode, parse_qs, urlparse
from typing import Optional, Dict, Any

class SpotifyAuth:
    """Handle Spotify OAuth authentication"""
    
    def __init__(self):
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8080/callback')
        self.scope = 'playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private'
        # token cache under project root /tokens/spotify.json
        self.tokens_dir = Path(__file__).resolve().parent.parent / 'tokens'
        self.tokens_file = self.tokens_dir / 'spotify.json'
        
        if not self.client_id or not self.client_secret:
            raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in environment variables")
    
    def get_auth_url(self) -> str:
        """Generate Spotify authorization URL"""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'show_dialog': 'true'
        }
        
        return f"https://accounts.spotify.com/authorize?{urlencode(params)}"
    
    def get_access_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post('https://accounts.spotify.com/api/token', data=data)
        response.raise_for_status()
        payload = response.json()
        # add absolute expiry timestamp
        payload['expires_at'] = int(time.time()) + int(payload.get('expires_in', 3600))
        return payload
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post('https://accounts.spotify.com/api/token', data=data)
        response.raise_for_status()
        payload = response.json()
        # ensure refresh_token persists if not returned
        if 'refresh_token' not in payload or not payload['refresh_token']:
            payload['refresh_token'] = refresh_token
        payload['expires_at'] = int(time.time()) + int(payload.get('expires_in', 3600))
        return payload

    # -------------- Token cache helpers --------------
    def _load_cached_tokens(self):
        try:
            if self.tokens_file.exists():
                with open(self.tokens_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _save_cached_tokens(self, tokens):
        try:
            self.tokens_dir.mkdir(parents=True, exist_ok=True)
            with open(self.tokens_file, 'w', encoding='utf-8') as f:
                json.dump(tokens, f, indent=2)
        except Exception:
            pass

    def authenticate(self) -> dict:
        """Obtain a valid access token, using cache/refresh when possible."""
        # 1) Try cached tokens
        cached = self._load_cached_tokens()
        if cached:
            now = int(time.time())
            if cached.get('access_token') and cached.get('expires_at', 0) > now + 30:
                return cached
            if cached.get('refresh_token'):
                try:
                    refreshed = self.refresh_access_token(cached['refresh_token'])
                    self._save_cached_tokens(refreshed)
                    return refreshed
                except Exception:
                    pass
        # 2) Try env-provided refresh token
        env_refresh = os.getenv('SPOTIFY_REFRESH_TOKEN')
        if env_refresh:
            try:
                refreshed = self.refresh_access_token(env_refresh)
                self._save_cached_tokens(refreshed)
                return refreshed
            except Exception:
                pass
        # 3) Fallback to interactive auth
        tokens = self.authenticate_interactive()
        # persist tokens (includes refresh_token)
        self._save_cached_tokens(tokens)
        return tokens
    
    def authenticate_interactive(self) -> Dict[str, Any]:
        """Interactive authentication flow"""
        print("🔐 Starting Spotify authentication...")
        print(f"Opening browser to: {self.get_auth_url()}")
        
        # Open browser
        webbrowser.open(self.get_auth_url())
        
        # Start simple HTTP server to catch callback
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading
        
        auth_code = None
        
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                nonlocal auth_code
                if self.path.startswith('/callback'):
                    # Parse the code from URL
                    parsed = urlparse(self.path)
                    query_params = parse_qs(parsed.query)
                    auth_code = query_params.get('code', [None])[0]
                    
                    if auth_code:
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'<html><body><h1>Authentication successful!</h1><p>You can close this window.</p></body></html>')
                    else:
                        self.send_response(400)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'<html><body><h1>Authentication failed!</h1><p>No authorization code received.</p></body></html>')
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Suppress log messages
        
        # Start server
        server = HTTPServer(('localhost', 8080), CallbackHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        print("⏳ Waiting for authentication... (check your browser)")
        
        # Wait for callback
        timeout = 300  # 5 minutes
        start_time = time.time()
        while auth_code is None and (time.time() - start_time) < timeout:
            time.sleep(1)
        
        server.shutdown()
        
        if auth_code is None:
            raise TimeoutError("Authentication timed out")
        
        print("✅ Authorization code received!")
        
        # Exchange code for tokens
        tokens = self.get_access_token(auth_code)
        print("✅ Access token obtained!")
        
        return tokens

import io, zipfile
from typing import List
from database.models import Account

def create_session_zip_file(accounts: List[Account]) -> io.BytesIO:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for acc in accounts:
            # --- THIS IS THE FIX: The session_file is already bytes, no need to encode. ---
            zf.writestr(f"{acc.phone_number}.session", acc.session_file)
    zip_buffer.seek(0)
    return zip_buffer
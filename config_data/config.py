from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    bot_token: SecretStr
    admin_ids_str: str = Field(..., alias='ADMIN_IDS')
    required_channels_str: str = Field(..., alias='REQUIRED_CHANNELS')
    db_url: str = Field(..., alias='DB_URL')
    admin_channel_id: int = Field(..., alias='ADMIN_CHANNEL_ID')
    support_contact: str = Field("@YourSupportUsername", alias='SUPPORT_CONTACT')
    api_id: int = Field(..., alias='API_ID')
    api_hash: str = Field(..., alias='API_HASH')
    # --- ADD THIS LINE ---
    crypto_bot_token: SecretStr = Field(..., alias='CRYPTO_BOT_TOKEN')

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    
    @property
    def admin_ids(self) -> list[int]:
        return [int(admin_id.strip()) for admin_id in self.admin_ids_str.split(',')]
    
    @property
    def required_channels(self) -> list[str]:
        return [channel.strip() for channel in self.required_channels_str.split(',')]

config = Settings()
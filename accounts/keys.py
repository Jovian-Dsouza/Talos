"""Custodial wallets: sr25519 keypairs held by the backend, mnemonics encrypted at rest.

CustodialWallet has the coldkey / coldkeypub / hotkey shape the Bittensor SDK and http_auth accept,
so no wallet files are needed.
"""

from dataclasses import dataclass

from bittensor_core import Keypair
from cryptography.fernet import Fernet, InvalidToken


class KeyVaultError(RuntimeError):
    """The encryption key is missing, malformed or does not match the stored data."""


@dataclass(frozen=True)
class CustodialWallet:
    coldkey: Keypair
    coldkeypub: Keypair
    hotkey: Keypair

    @property
    def coldkey_ss58(self) -> str:
        return self.coldkey.ss58_address

    @property
    def hotkey_ss58(self) -> str:
        return self.hotkey.ss58_address


@dataclass(frozen=True)
class SealedWallet:
    """Encrypted mnemonics plus the public addresses, as stored in the users table."""

    coldkey_ss58: str
    hotkey_ss58: str
    enc_coldkey: str
    enc_hotkey: str


class KeyVault:
    def __init__(self, secret: str) -> None:
        try:
            self._fernet = Fernet(secret.encode())
        except (ValueError, TypeError) as exc:
            raise KeyVaultError("WALLET_ENCRYPTION_KEY must be a urlsafe base64 32 byte key") from exc

    def seal_mnemonic(self, mnemonic: str) -> str:
        return self._fernet.encrypt(mnemonic.encode()).decode()

    def open_mnemonic(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise KeyVaultError("stored key does not decrypt with this WALLET_ENCRYPTION_KEY") from exc

    def create(self) -> SealedWallet:
        cold_mnemonic, hot_mnemonic = Keypair.generate_mnemonic(), Keypair.generate_mnemonic()
        cold, hot = Keypair.create_from_mnemonic(cold_mnemonic), Keypair.create_from_mnemonic(hot_mnemonic)
        return SealedWallet(
            coldkey_ss58=cold.ss58_address,
            hotkey_ss58=hot.ss58_address,
            enc_coldkey=self.seal_mnemonic(cold_mnemonic),
            enc_hotkey=self.seal_mnemonic(hot_mnemonic),
        )

    def open(self, sealed: SealedWallet) -> CustodialWallet:
        cold = Keypair.create_from_mnemonic(self.open_mnemonic(sealed.enc_coldkey))
        hot = Keypair.create_from_mnemonic(self.open_mnemonic(sealed.enc_hotkey))
        return CustodialWallet(coldkey=cold, coldkeypub=Keypair(ss58_address=cold.ss58_address), hotkey=hot)


def wallet_from_mnemonics(coldkey_mnemonic: str, hotkey_mnemonic: str) -> CustodialWallet:
    """Treasury and validator keys supplied through environment variables."""
    cold = Keypair.create_from_mnemonic(coldkey_mnemonic)
    hot = Keypair.create_from_mnemonic(hotkey_mnemonic)
    return CustodialWallet(coldkey=cold, coldkeypub=Keypair(ss58_address=cold.ss58_address), hotkey=hot)

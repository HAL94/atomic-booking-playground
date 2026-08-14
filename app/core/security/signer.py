from typing import Any

from fastapi import HTTPException
from itsdangerous import SignatureExpired, URLSafeTimedSerializer

__secret_cookie_key__ = "a356258a081495d33581a3aeb850666083cf6009ae29021e7201f9199e6db750"


class CookieSigner:
    """A helper class that will sign a string value to obfuscate plain strings, useful for cookies"""

    def __init__(self):
        self._secret_key = __secret_cookie_key__
        self._cookie_salt = "cookie-salt"
        self.signer = URLSafeTimedSerializer(self._secret_key, self._cookie_salt)

    def dumps(self, obj: Any, salt: str | bytes | None = None) -> str:
        """
        Safely sign a value and obfuscute it.


        :param obj: the data to encode
        :type obj: Any
        :param salt: Signer salt
        :type salt: str | bytes | None
        :return: Signed value
        :rtype: str
        """
        return self.signer.dumps(obj, salt)

    def loads(self, signed_data: Any, max_age: int | None = None) -> str:
        """
        Get original data from signed data. Optionally check if data is expired by passing max_age

        :param signed_data: data previously encoded
        :type signed_data: Any
        :param max_age: time in seconds to check validity of encoded data
        :type max_age: int | None
        :return: original data
        :rtype: str
        """
        try:
            data = self.signer.loads(signed_data, max_age=max_age)
            return data
        except SignatureExpired:
            raise HTTPException(status_code=401, detail="Cookie has expired")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid cookie signature")

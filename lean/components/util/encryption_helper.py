# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
from typing import List
from pathlib import Path
from base64 import b64decode, b64encode
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from lean.components.config.project_config_manager import ProjectConfigManager
from lean.models.api import QCProject, QCFullFile

def calculate_md5(input_string: str):
    """Calculate the md5 hash of a string

    :param input_string: The string to hash
    :return: The md5 hash of the string
    """
    import hashlib
    return hashlib.md5(input_string.encode()).hexdigest()

def get_b64_encoded(key: str) -> bytes:
    """Encode a string to base64

    :param key: The string to encode
    :return: The base64 encoded string
    """
    return b64encode(key.encode('utf-8'))

def get_project_key(project_key_path: Path, organization_id: str) -> str:
    """Get the project key from the project key file

    :param project_key_path: The path to the project key file
    :return: The project key
    """
    with open(project_key_path, 'r') as f:
        content = f.read()
        key_for_aes = _get_fixed_length_key_from_user_full_length_key(content, organization_id.encode('utf-8'))
        return key_for_aes

def get_project_key_hash(project_key_path: Path):
    """Get the MD5 hash from the project key file

    :param project_key_path: The path to the project key file
    :return: The project iv
    """
    with open(project_key_path, 'r', encoding='utf-8') as f:
        content = f.read()
        return calculate_md5(content)
    
def get_project_iv(project_key_path: Path):
    """Get the project iv from the project key file

    :param project_key_path: The path to the project key file
    :return: The project iv
    """
    key_id = get_project_key_hash(project_key_path)
    return key_id[:16]

def get_decrypted_file_content_for_project(project: Path, source_files: List[Path], encryption_key: Path, project_config_manager: ProjectConfigManager, organization_id: str) -> List[str]:
    project_config = project_config_manager.get_project_config(project)

    # Check if the project is already encrypted
    areProjectFilesAlreadyEncrypted = project_config.get('encrypted', False)

    # Check if there is mismatch of keys
    local_encryption_key_path = project_config.get('encryption-key-path', None)
    if local_encryption_key_path and encryption_key and Path(local_encryption_key_path) != encryption_key:
        raise RuntimeError(f"Registered encryption key {local_encryption_key_path} is different from the one provided {encryption_key}")
    
    project_key = get_project_key(encryption_key, organization_id)
    project_iv = get_project_iv(encryption_key)
    decrypted_data = []
    for file in source_files:
        try:
            # lets read and decrypt the file
            with open(file, 'r') as f:
                encrypted = f.read()
                if not areProjectFilesAlreadyEncrypted:
                    decrypted = encrypted
                else:
                    decrypted = decrypt_file_content(get_b64_encoded(project_key), get_b64_encoded(project_iv), encrypted)
                decrypted_data.append(decrypted)
        except Exception as e:
            raise RuntimeError(f"Failed to decrypt file {file} with error {e}")
    return decrypted_data

def decrypt_file_content(b64_encoded_key: bytes, b64_encoded_iv: bytes, b64_encoded_content: str) -> str:
    # remove new line characters that we added during encryption
    b64_encoded_content = b64_encoded_content.replace('\n', '')
    b64_encoded_content = b64_encoded_content.strip()
    content = b64decode(b64_encoded_content.encode('utf-8'))
    key = b64decode(b64_encoded_key)
    init_vector = b64decode(b64_encoded_iv)
    # Setup module-specific classes
    cipher = Cipher(algorithms.AES(key), modes.CBC(init_vector))
    decryptor = cipher.decryptor()

    plaintext = decryptor.update(content) + decryptor.finalize()
    # Unpad the decrypted data
    unpadder = padding.PKCS7(128).unpadder()
    unpadded_data = unpadder.update(plaintext) + unpadder.finalize()
    return unpadded_data.decode('utf-8').replace("\r\n", "\n")

def get_encrypted_file_content_for_project(project: Path, source_files: List[Path], encryption_key: Path, project_config_manager: ProjectConfigManager, organization_id: str) -> List[str]:
    project_config = project_config_manager.get_project_config(project)

    # Check if the project is already encrypted
    areProjectFilesAlreadyEncrypted = project_config.get('encrypted', False)

    # Check if there is mismatch of keys
    local_encryption_key_path = project_config.get('encryption-key-path', None)
    if local_encryption_key_path and encryption_key and Path(local_encryption_key_path) != encryption_key:
        raise RuntimeError(f"Registered encryption key {local_encryption_key_path} is different from the one provided {encryption_key}")

    project_key = get_project_key(encryption_key, organization_id)
    project_iv = get_project_iv(encryption_key)
    encrypted_data: List[str] = []
    for file in source_files:
        try:
            # lets read and decrypt the file
            with open(file, 'rb') as f:
                plain_text = f.read()
                if areProjectFilesAlreadyEncrypted:
                    encrypted = plain_text
                else:
                    encrypted = encrypt_file_content(get_b64_encoded(project_key), get_b64_encoded(project_iv), plain_text)
                encrypted_data.append(encrypted)
        except Exception as e:
            raise RuntimeError(f"Failed to encrypt file {file} with error {e}")
    return encrypted_data

def encrypt_file_content(b64_encoded_key: bytes, b64_encoded_iv: bytes, content: bytes) -> str:
    key = b64decode(b64_encoded_key)
    init_vector = b64decode(b64_encoded_iv)
    plain_text = _pad(content, 16)
    # Setup module-specific classes
    cipher = Cipher(algorithms.AES(key), modes.CBC(init_vector))
    encryptor = cipher.encryptor()

    # Encrypt and decrypt data
    cipher_text = encryptor.update(plain_text) + encryptor.finalize()
    encrypted_content = b64encode(cipher_text).decode('utf-8')
    # let's make it user friendly and add new lines, same as local platform
    regex = r".{1,80}"
    chunks = re.findall(regex, encrypted_content)
    return '\n'.join(chunks)

def get_decrypted_content_from_cloud_project(project: QCProject, cloud_files: List[QCFullFile], encryption_key: Path, organization_id: str) -> List[QCFullFile]:
    # Check if the project is already encrypted
    if not project.encrypted or project.encryptionKey.id != get_project_key_hash(encryption_key):
        return cloud_files
    
    project_key = get_project_key(encryption_key, organization_id)
    project_iv = get_project_iv(encryption_key)
    for cloud_file in cloud_files:
        try:
            decrypted = decrypt_file_content(get_b64_encoded(project_key), get_b64_encoded(project_iv), cloud_file.content)
            cloud_file.content = decrypted
        except Exception as e:
            raise RuntimeError(f"Failed to decrypt file {cloud_file} with error {e}")
    return cloud_files

def get_encrypted_content_from_cloud_project(project: QCProject, cloud_files: List[QCFullFile], encryption_key: Path, organization_id: str) -> List[QCFullFile]:
    # Check if the project is already encrypted
    if project.encrypted:
        if encryption_key is not None and project.encryptionKey and project.encryptionKey.id != get_project_key_hash(encryption_key):
            raise RuntimeError(f"Registered encryption key {project.encryptionKey.id} is different from the one provided {encryption_key}")
        return cloud_files

    project_key = get_project_key(encryption_key, organization_id)
    project_iv = get_project_iv(encryption_key)
    for cloud_file in cloud_files:
        try:
            encrypted = encrypt_file_content(get_b64_encoded(project_key), get_b64_encoded(project_iv), cloud_file.content.encode('utf-8'))
            cloud_file.content = encrypted
        except Exception as e:
            raise RuntimeError(f"Failed to decrypt file {cloud_file} with error {e}")
    return cloud_files

def _pad(data, block_size):
    """Padding function for AES encryption

    :param data: data to pad
    :param block_size: required block size
    :return: padded data
    """
    padding_length = block_size - (len(data) % block_size)
    return data + bytes([padding_length] * padding_length)

def _get_fixed_length_key_from_user_full_length_key(password: str, salt: bytes):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=16,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode()).hex()


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

from typing import List
from pathlib import Path
from lean.components.util.logger import Logger
from base64 import b64decode, b64encode
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from lean.models.encryption import ActionType
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.models.api import QCProject, QCFullFile
from lean.components.config.storage import Storage
from lean.components.api.api_client import APIClient
from lean.components.util.organization_manager import OrganizationManager

def calculate_md5(input_string: str):
    """Calculate the md5 hash of a string

    :param input_string: The string to hash
    :return: The md5 hash of the string
    """
    from hashlib import md5
    return md5(input_string.encode()).hexdigest()

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
    with open(project_key_path, 'r', encoding='utf-8', newline='') as f:
        content = f.read()
        key_for_aes = _get_fixed_length_key_from_user_full_length_key(content, organization_id.encode('utf-8'))
        return key_for_aes

def get_project_key_hash(project_key_path: Path):
    """Get the MD5 hash from the project key file

    :param project_key_path: The path to the project key file
    :return: The project iv
    """
    with open(project_key_path, 'r', encoding='utf-8', newline='') as f:
        content = f.read()
        return calculate_md5(content)

def get_project_iv(project_key_path: Path):
    """Get the project iv from the project key file

    :param project_key_path: The path to the project key file
    :return: The project iv
    """
    key_id = get_project_key_hash(project_key_path)
    return key_id[:16]

def are_encryption_keys_equal(key1: Path, key2: Path) -> bool:
    """Check if two encryption keys are equal

    :param key1: The first key to compare
    :param key2: The second key to compare
    :return: True if the keys are equal, False otherwise
    """
    if key1 is None and key2 is None:
        return True
    if key1 is None or key2 is None:
        return False
    return get_project_key_hash(key1) == get_project_key_hash(key2)

def get_decrypted_file_content_for_local_project(project: Path, source_files: List[Path], encryption_key: Path, project_config_manager: ProjectConfigManager, organization_id: str) -> List[str]:
    project_config = project_config_manager.get_project_config(project)

    # Check if the project is already encrypted
    areProjectFilesAlreadyEncrypted = project_config.get('encrypted', False)

    # Check if there is mismatch of keys
    _validate_key_state_for_local_project(project_config, encryption_key)

    project_key = get_project_key(encryption_key, organization_id)
    project_iv = get_project_iv(encryption_key)
    encoded_project_key = project_key.encode('utf-8')
    encoded_project_iv = project_iv.encode('utf-8')
    decrypted_data = []
    for file in source_files:
        try:
            # lets read and decrypt the file
            with open(file, 'r', encoding="utf-8") as f:
                encrypted = f.read()
                if not areProjectFilesAlreadyEncrypted:
                    decrypted = encrypted
                else:
                    decrypted = _decrypt_file_content(encoded_project_key, encoded_project_iv, encrypted)
                decrypted_data.append(decrypted)
        except Exception as e:
            raise RuntimeError(f"Failed to decrypt file {file} with error {e}")
    return decrypted_data

def get_encrypted_file_content_for_local_project(project: Path, source_files: List[Path], encryption_key: Path, project_config_manager: ProjectConfigManager, organization_id: str) -> List[str]:
    project_config = project_config_manager.get_project_config(project)

    # Check if the project is already encrypted
    areProjectFilesAlreadyEncrypted = project_config.get('encrypted', False)

    # Check if there is mismatch of keys
    _validate_key_state_for_local_project(project_config, encryption_key)

    project_key = get_project_key(encryption_key, organization_id)
    project_iv = get_project_iv(encryption_key)
    encoded_project_key = project_key.encode('utf-8')
    encoded_project_iv = project_iv.encode('utf-8')
    encrypted_data: List[str] = []
    for file in source_files:
        try:
            # lets read and decrypt the file
            with open(file, 'r', encoding= "utf-8") as f:
                plain_text = f.read()
                if areProjectFilesAlreadyEncrypted:
                    encrypted = plain_text
                else:
                    encrypted = _encrypt_file_content(encoded_project_key, encoded_project_iv, plain_text.encode('utf-8'))
                encrypted_data.append(encrypted)
        except Exception as e:
            raise RuntimeError(f"Failed to encrypt file {file} with error {e}")
    return encrypted_data

def get_and_validate_user_input_encryption_key(user_input_key: Path, project_config_encryption_key: Path) -> str:
    if project_config_encryption_key is not None and Path(project_config_encryption_key).exists():
        project_config_encryption_key = Path(project_config_encryption_key)
    if project_config_encryption_key is None and user_input_key is None:
        raise RuntimeError("No encryption key was provided, please provide one using --key")
    elif project_config_encryption_key is None:
        project_config_encryption_key = user_input_key
    elif user_input_key is not None and project_config_encryption_key != user_input_key:
        raise RuntimeError(f"Provided encryption key ({user_input_key}) does not match the encryption key in the project ({project_config_encryption_key})")
    return project_config_encryption_key

def validate_user_inputs_for_cloud_push_pull_commands(encrypt: bool, decrypt: bool, key: Path):
    if encrypt and decrypt:
        raise RuntimeError(f"Cannot encrypt and decrypt at the same time.")
    if key is None and (encrypt or decrypt):
        raise RuntimeError(f"Encryption key is required when encrypting or decrypting.")
    if key is not None and not encrypt and not decrypt:
            raise RuntimeError(f"Encryption key can only be specified when encrypting or decrypting.")

def validate_encryption_key_registered_with_cloud(user_key: Path, organization_manager: OrganizationManager, api_client: APIClient):
    # lets check if the given key is registered with the cloud
    organization_id = organization_manager.try_get_working_organization_id()
    available_encryption_keys = api_client.encryption_keys.list(organization_id)['keys']
    encryption_key_id = get_project_key_hash(user_key)
    if (not any(found_key for found_key in available_encryption_keys if found_key['hash'] == encryption_key_id)):
        raise RuntimeError(f"Given encryption key is not registered with the cloud.")

def validate_key_and_encryption_state_for_cloud_project(project: QCProject, local_project_encryption_state: bool, encryption_key: Path, local_encryption_key: Path, logger:Logger) -> None:
    if not encryption_key and project.encryptionKey and local_encryption_key and local_encryption_key.exists() and get_project_key_hash(local_encryption_key) != project.encryptionKey.id:
        raise RuntimeError(f"Encryption Key mismatch. Local Project Key: {local_encryption_key}. Cloud Project Key: {project.encryptionKey.name}. Please provide correct encryption key for project '{project.name}' to proceed.")
    if not encryption_key and bool(project.encrypted) != bool(local_project_encryption_state):
        logger.debug(f"Force Overwrite: Project encryption state mismatch. Local Project Encrypted: {bool(local_project_encryption_state)}. Cloud Project Encrypted: {bool(project.encrypted)}.")
        return
    if encryption_key and project.encryptionKey and get_project_key_hash(encryption_key) != project.encryptionKey.id:
        raise RuntimeError(f"Encryption Key mismatch. Local Project Key hash: {get_project_key_hash(encryption_key)}. Cloud Project Key Hash: {project.encryptionKey.id}. Please provide correct encryption key for project '{project.name}' to proceed.")

def get_appropriate_files_from_cloud_project(project: QCProject, cloud_files: List[QCFullFile], encryption_key: Path, organization_id: str, encryption_action: ActionType) -> List[QCFullFile]:
    if encryption_action == ActionType.DECRYPT:
        return _get_decrypted_content_from_cloud_project(project, cloud_files, encryption_key, organization_id)
    return _get_encrypted_content_from_cloud_project(project, cloud_files, encryption_key, organization_id)

def get_appropriate_files_from_local_project(project: Path, paths: List[Path], encryption_key: Path, project_config_manager: ProjectConfigManager, organization_id: str, encryption_action: ActionType) -> List[str]:
    if encryption_action == ActionType.ENCRYPT:
        return get_encrypted_file_content_for_local_project(project, paths, encryption_key, project_config_manager, organization_id)
    return get_decrypted_file_content_for_local_project(project, paths, encryption_key,project_config_manager, organization_id)


def _validate_key_state_for_local_project(project_config: Storage, encryption_key: Path):
    local_encryption_key_path = project_config.get('encryption-key-path', None)
    if local_encryption_key_path and encryption_key and Path(local_encryption_key_path) != encryption_key:
        raise RuntimeError(f"Registered encryption key {local_encryption_key_path} is different from the one provided {encryption_key}")

def _decrypt_file_content(key: bytes, init_vector: bytes, b64_encoded_content: str) -> str:
    # remove new line characters that we added during encryption
    b64_encoded_content = b64_encoded_content.replace('\n', '')
    b64_encoded_content = b64_encoded_content.strip()
    content = b64decode(b64_encoded_content.encode('utf-8'))
    # Setup module-specific classes
    cipher = Cipher(algorithms.AES(key), modes.CBC(init_vector))
    decryptor = cipher.decryptor()

    plaintext = decryptor.update(content) + decryptor.finalize()
    # Unpad the decrypted data
    unpadder = padding.PKCS7(128).unpadder()
    unpadded_data = unpadder.update(plaintext) + unpadder.finalize()
    return unpadded_data.decode('utf-8').replace("\r\n", "\n")

def _encrypt_file_content(key: bytes, init_vector: bytes, content: bytes) -> str:
    plain_text = _pad(content, 16)
    # Setup module-specific classes
    cipher = Cipher(algorithms.AES(key), modes.CBC(init_vector))
    encryptor = cipher.encryptor()

    # Encrypt and decrypt data
    cipher_text = encryptor.update(plain_text) + encryptor.finalize()
    encrypted_content = b64encode(cipher_text).decode('utf-8')
    # let's make it user friendly and add new lines, same as local platform
    regex = r".{1,80}"
    from re import findall
    chunks = findall(regex, encrypted_content)
    return '\n'.join(chunks)

def _get_decrypted_content_from_cloud_project(project: QCProject, cloud_files: List[QCFullFile], encryption_key: Path, organization_id: str) -> List[QCFullFile]:
    # Check if the project is already encrypted
    if not project.encrypted or project.encryptionKey.id != get_project_key_hash(encryption_key):
        return cloud_files

    project_key = get_project_key(encryption_key, organization_id)
    project_iv = get_project_iv(encryption_key)
    encoded_project_key = project_key.encode('utf-8')
    encoded_project_iv = project_iv.encode('utf-8')
    for cloud_file in cloud_files:
        try:
            decrypted = _decrypt_file_content(encoded_project_key, encoded_project_iv, cloud_file.content)
            cloud_file.content = decrypted
        except Exception as e:
            raise RuntimeError(f"Failed to decrypt file {cloud_file} with error {e}")
    return cloud_files

def _get_encrypted_content_from_cloud_project(project: QCProject, cloud_files: List[QCFullFile], encryption_key: Path, organization_id: str) -> List[QCFullFile]:
    # Check if the project is already encrypted
    if project.encrypted:
        if encryption_key is not None and project.encryptionKey and project.encryptionKey.id != get_project_key_hash(encryption_key):
            raise RuntimeError(f"Registered encryption key {project.encryptionKey.id} is different from the one provided {encryption_key}")
        return cloud_files

    project_key = get_project_key(encryption_key, organization_id)
    project_iv = get_project_iv(encryption_key)
    encoded_project_key = project_key.encode('utf-8')
    encoded_project_iv = project_iv.encode('utf-8')
    for cloud_file in cloud_files:
        try:
            encrypted = _encrypt_file_content(encoded_project_key, encoded_project_iv, cloud_file.content.encode('utf-8'))
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
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=16,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode()).hex()



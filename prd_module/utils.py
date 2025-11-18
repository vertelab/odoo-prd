import io
import time
import tarfile
import logging
import paramiko

_logger = logging.getLogger(__name__)

class FileWriter:
    """Abstract base class for file writing strategies"""

    def write_file(self, dir_path, filename, content):
        """Write a file and return its path"""
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

class TarFileWriter(FileWriter):
    """Writer that adds files to a tar archive"""

    def __init__(self, module_path):
        self.tar_file = io.BytesIO()
        self.tar = tarfile.open(fileobj=self.tar_file, mode='w:gz')
        self.module_path = module_path        

    def get_writer(self):
        return self.tar

    def write_file(self, dir_path, filename, content):
        full_dir = f"{self.module_path}{dir_path}"
        arcname = f"{full_dir}{filename}"
        content = content if content else ""
        data = content.encode('utf-8')
        fileobj = io.BytesIO(data)
        tarinfo = tarfile.TarInfo(name=arcname)
        tarinfo.size = len(data)
        tarinfo.mtime = time.time()
        self.tar.addfile(tarinfo, fileobj=fileobj)
        return arcname

    def close(self):
        self.tar.close()
        self.tar_file.close()

class SFTPFileWriter(FileWriter):
    """Writer that uploads files via SFTP"""

    def __init__(self, username,hostname,port,module_path):
        self.username = username
        self.hostname = hostname
        self.port = port
        self.module_path = module_path
        self.ssh = paramiko.SSHClient()
        self.sftp = self._setup_paramiko()

    def _setup_paramiko(self):
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname=self.hostname, username=self.username, port=self.port)
        sftp = self.ssh.open_sftp()
        return sftp

    def write_file(self, dir_path, filename, content):
        full_path = f"{self.module_path}{dir_path}"
        self._mkdir_safe(full_path)
        file_path = f"{full_path}{filename}"
        with self.sftp.file(file_path, 'w+') as remote_file:
            remote_file.write(content if content else "")
            remote_file.close()
        return file_path

    def _mkdir_safe(self, dir_path, mode=0o775):
        """Recursively create directories"""
        if not dir_path or dir_path == '/':
            return

        # Remove trailing slash
        dir_path = dir_path.rstrip('/')

        # Check if directory already exists
        try:
            self.sftp.stat(dir_path)
            return  # Directory exists
        except IOError:
            pass  # Directory doesn't exist, continue to create it

        # Get parent directory
        parent = dir_path.rsplit('/', 1)[0]
        if parent and parent != '/':
            # Recursively create parent directory
            self._mkdir_safe(parent, mode)

        # Create this directory
        try:
            self.sftp.mkdir(dir_path, mode)
        except IOError as e:
            # Ignore if directory was created by another process
            try:
                self.sftp.stat(dir_path)
            except IOError:
                _logger.warning(
                    f"Got error {e} when making directory {dir_path} with sftp on remote host."
                )

    def close(self):
        self.sftp.close()
        self.ssh.close()
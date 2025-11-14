import io
import time
import tarfile
import logging

_logger = logging.getLogger(__name__)

class FileWriter:
    """Abstract base class for file writing strategies"""

    def write_file(self, dir_path, filename, content):
        """Write a file and return its path"""
        raise NotImplementedError


class TarFileWriter(FileWriter):
    """Writer that adds files to a tar archive"""

    def __init__(self, tar, module_path):
        self.tar = tar
        self.module_path = module_path

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


class SFTPFileWriter(FileWriter):
    """Writer that uploads files via SFTP"""

    def __init__(self, sftp, module_path):
        self.sftp = sftp
        self.module_path = module_path

    def write_file(self, dir_path, filename, content):
        full_path = f"{self.module_path}{dir_path}"
        self._mkdir_safe(full_path)
        file_path = f"{full_path}{filename}"
        with self.sftp.file(file_path, 'w+') as remote_file:
            remote_file.write(content if content else "")
            remote_file.close()
        return file_path

    def _mkdir_safe(self, dir_path, mode=0o775):
        try:
            self.sftp.mkdir(dir_path, mode)
        except IOError as e:
            _logger.warning(
                f"Got this error {e} when making directory with sftp on remote host.\n"
                f"It is likely that the directory already exists, will skip creating it."
            )

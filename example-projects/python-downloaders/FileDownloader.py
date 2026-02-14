import os
import pycurl
import hashlib
import concurrent.futures
import requests
import os
import time
import bz2
import shutil
import subprocess
from pathlib import Path
import traceback

last_percent = {'value': -5}
def progress_callback(bytes_downloaded, total_bytes,filename):
    percent = (bytes_downloaded / total_bytes) * 100 if total_bytes else 0
    if filename+'value' not in last_percent:
        last_percent[filename+'value']=-5
    if percent - last_percent[filename+'value'] >= 5 or percent == 100:
        print(f"Downloaded {bytes_downloaded}/{total_bytes} bytes ({percent:.2f}%) : {filename}")
        last_percent[filename+'value'] = percent
        if percent==100:
            last_percent[filename+'value']=-5


def decompress_bz2_file(filepath,decompressor="internal"):
        """Decompresses a .bz2 file."""
        filepath = Path(filepath)
        output_path = filepath.with_suffix('')
        
        if decompressor in ["bzip2", "lbzip2"]:
            command = [decompressor, "-d", "-k","-f", str(filepath)]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
                return f"Successfully decompressed {filepath} using {decompressor}"
            except subprocess.CalledProcessError as e:
                import traceback
                traceback.print_exc()
                return f"Failed to decompress {filepath} with {decompressor}. Stderr: {e.stderr}"

        # Fallback to Python's bz2 module
        try:
            with bz2.open(filepath, "rb") as f_in:
                with open(output_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return f"Successfully decompressed {filepath} using internal bz2 library"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Failed with internal bz2: {e}"

def decompress_bz2_command(filepath,decompressor="bzip2"):
    try:
        return decompress_bz2_file(filepath,decompressor)
    except Exception as e:
        import traceback
        traceback.print_exc()
    #return decompress_bz2_file(filepath, decompressor=decompressor)


class FileDownloader:

	def __init__(self, download_dir, chunk_size=8192, callback=None):
		self.download_dir = download_dir
		self.chunk_size = chunk_size
		self.callback = callback
	
	def _md5sum(self, file_path):
		"""Compute md5 hash of a file asynchronously."""
		hash_md5 = hashlib.md5()

		with open(file_path, "rb") as f:
			while True:
				chunk = f.read(self.chunk_size)
				if not chunk:
					break
				hash_md5.update(chunk)				
		return hash_md5.hexdigest()

    
	def _validate_file(self, file_path, expected_size=None, expected_md5=None):
		if not os.path.exists(file_path):
			return False
		if expected_size is not None and os.path.getsize(file_path) != expected_size:
			return False
		if expected_md5 is not None:
			actual_md5 = self._md5sum(file_path)
			if actual_md5 != expected_md5:
				return False
		return True

	def download(self, url, filename=None, expected_size=None, expected_md5=None):

		if filename==None:
			filename = os.path.basename(url)

			if not filename:
				raise ValueError("Cannot determine filename from URL. Please provide a filename.")
				
		file_path = os.path.join(self.download_dir, filename)

		# Check if file already exists and is valid
		if self._validate_file(file_path, expected_size, expected_md5):
			print(f"File {file_path} already exists and is valid. Skipping download.")
			return file_path

		md5 = hashlib.md5()
		received = 0

		# Try to get total bytes from Content-Length header
		total_bytes = None
		c = pycurl.Curl()
		c.setopt(c.URL, url)
		c.setopt(c.NOBODY, 1)
		c.perform()
		try:
			total_bytes = int(c.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD))
		except Exception:
			import traceback
			traceback.print_exc()
			total_bytes = expected_size
		c.close()

		def write_callback(data):
			nonlocal received
			f.write(data)
			md5.update(data)
			received += len(data)
			if self.callback:
				self.callback(received, total_bytes,filename)

		with open(file_path, 'wb') as f:
			c = pycurl.Curl()
			c.setopt(c.URL, url)
			c.setopt(c.WRITEFUNCTION, write_callback)
			c.perform()
			c.close()

		# Check file size
		if expected_size is not None and received != expected_size:
			raise ValueError(f"Size mismatch: expected {expected_size}, got {received}")

		# Check MD5
		if expected_md5 is not None and md5.hexdigest() != expected_md5:
			raise ValueError("MD5 checksum mismatch")

		return file_path


        


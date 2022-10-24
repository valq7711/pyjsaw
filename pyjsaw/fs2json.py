import os
import re
import threading

from typing import Union

import hashlib
from .xdict import XDict

FILE_MASK_REX = re.compile(r'(.(?!\.min))+.\.(py|vuepy|pyj|css|html|js|md|txt|sql|prj)$', flags=re.I)


def to_bytes(obj, charset='utf-8', errors='strict'):
        if obj is None:
            return None
        if isinstance(obj, (bytes, bytearray)):
            return bytes(obj)
        if isinstance(obj, str):
            return obj.encode(charset, errors)
        raise TypeError('Expected bytes')


def md5_hash(text):
    """Generate an md5 hash with the given text."""
    return hashlib.md5(to_bytes(text)).hexdigest()


class FS2Json:
    _local = threading.local()

    def __init__(self):
        self.last_id = 0

    @property
    def last_id(self):
        return self._local.last_id

    @last_id.setter
    def last_id(self, v):
        self._local.last_id = v
        return v

    def get_id(self):
        self.last_id += 1
        return '0' if self.last_id == 0 else f'ID{self.last_id}'

    @staticmethod
    def safe_read(fp):
        with open(fp, 'r', encoding='utf8') as f:
            ret = f.read()
        return ret

    def get_file(self, fp, parent_id):
        stat = os.stat(fp)
        content = self.safe_read(fp)
        ret = dict(
            id=self.get_id(),
            name=os.path.basename(fp),
            parent=parent_id,
            content=content,
            ctime=int(stat.st_ctime * 1000),
            mtime=int(stat.st_mtime * 1000),
            md5_hash=md5_hash(content)
        )
        return ret

    def get_dir(self, pth_to_dir, parent_id, files: dict, dirs: dict,
                dir_patt: Union[str, dict], file_mask: re.Pattern):
        ret = dict(
            id=self.get_id(),
            name=os.path.basename(pth_to_dir.rstrip('/')),
            parent=parent_id,
            content=[]
        )
        for it in os.listdir(pth_to_dir):
            fp = os.path.join(pth_to_dir, it)
            if os.path.isfile(fp):
                if file_mask.match(it):
                    fl = self.get_file(fp, ret['id'])
                    files[fl['id']] = fl
                    ret['content'].append(fl['id'])
                else:
                    continue
            elif dir_patt is not None:
                if dir_patt == '*':
                    sub_dir_patt = '*'
                else:
                    sub_dir_patt = dir_patt.get(it, '*' if dir_patt.get('*') else None)
                if sub_dir_patt is not None:
                    d = self.get_dir(fp, ret['id'], files, dirs, sub_dir_patt, file_mask)
                    dirs[d['id']] = d
                    ret['content'].append(d['id'])
        return ret

    def dir_to_fs(self, root_d: str, dir_patt: dict = None, file_mask: re.Pattern = None):
        if file_mask is None:
            file_mask = FILE_MASK_REX
        self.last_id = -1
        dirs = {}
        files = {}
        root = self.get_dir(root_d, None, files, dirs, dir_patt, file_mask)
        root['name'] = ''
        dirs[root['id']] = root
        return dict(files=files, dirs=dirs, last_id=self.last_id)

    def validate_fdata(self, fdata, app_folder, must_exist=False):
        fdata = XDict(fdata)
        ret = XDict(md5_hash=None, error='', os_path=None)
        pth = fdata.path.strip()
        sanitize_pth_re = re.compile(r'\s*(\\|/)*([^\s]*)\s*$')
        pth = sanitize_pth_re.match(pth).groups()[1]
        ret.os_path = os_path = os.path.join(app_folder, pth)
        if must_exist and not os.path.exists(os_path):
            ret.error = 'it seems that path does not exist: %s' % os_path
        elif os.path.isdir(os_path):
            ret.error = 'path to a file was expected: %s [%s]' % (os_path, fdata.path)
        elif os.path.isfile(os_path):
            if not fdata.md5_hash:
                ret.error = 'md5_hash is required'
            elif md5_hash(self.safe_read(os_path)) != fdata.md5_hash:
                ret.error = 'file was changed on disk'
        elif os.path.exists(os_path):
            ret.error = 'path exists but it`s to never : %s' % os_path
        return ret

    def write_file(self, fdata, app_folder):
        ret = self.validate_fdata(fdata, app_folder)
        if ret.error:
            return ret
        content = fdata.get('content', '')
        read_content = getattr(content, 'read', lambda: content.encode('utf8'))
        content = read_content()
        with open(ret.os_path, 'wb') as fl:
            fl.write(content)
        ret.md5_hash = md5_hash(content)
        return ret

    def del_file(self, fdata, app_folder):
        ret = self.validate_fdata(fdata, app_folder, must_exist=True)
        if ret.error:
            return ret
        os.unlink(ret.os_path)
        ret.msg = 'done'
        return ret

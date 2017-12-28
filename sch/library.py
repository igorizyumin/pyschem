from PyQt5.QtCore import *
from sch.document import *


class PartLibrary(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.paths = ['./schlib/']
        self._docs = {}
        self._rebuildCache()

    def _rebuildCache(self):
        # first, build a list of dirs to search
        def getDirs(path, prefix):
            d = QDir(path)
            d.setFilter(QDir.Dirs | QDir.NoDotAndDotDot)
            out = [prefix]
            for name in d.entryList():
                out += getDirs(d.filePath(name), prefix + name + '/')
            return out

        dirs = []
        for p in self.paths:
            dirs.append((p, getDirs(p, '')))

        for path, dirlist in dirs:
            for dn in dirlist:
                d = QDir(path + dn)
                d.setFilter(QDir.Readable | QDir.Files)
                d.setNameFilters(['*.xsch'])
                files = d.entryList()
                for f in files:
                    try:
                        fp = d.filePath(f)
                        doc = MasterDocument(self)
                        doc.loadFromFile(fp)
                        self._docs[fp] = doc
                    except Exception as e:
                        print("Exception loading {}: {}".format(f, str(e)))

    def getSymList(self):
        out = []
        for path in self._docs:
            out.append((path, [s.name for s in self._docs[path].symbols]))
        return out

    def getSym(self, path, name):
        if path not in self._docs:
            return None
        doc = self._docs[path]
        for s in doc.symbols:
            if s.name == name:
                return s
        return None
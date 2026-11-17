import re, shutil, sys, zipfile

src = sys.argv[1]
tmp = src + ".tmp"
zin = zipfile.ZipFile(src)
names = set(zin.namelist())
ct = zin.read("[Content_Types].xml").decode("utf-8")
removed = []

def keep(m):
    part = m.group(1).lstrip("/")
    if part in names:
        return m.group(0)
    removed.append(part)
    return ""

ct2 = re.sub(r'<Override PartName="([^"]+)"[^>]*/>', keep, ct)
zout = zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = ct2.encode("utf-8") if item.filename == "[Content_Types].xml" else zin.read(item.filename)
    zout.writestr(item, data)
zout.close()
zin.close()
shutil.move(tmp, src)
print("removed phantom overrides:", removed if removed else "none")

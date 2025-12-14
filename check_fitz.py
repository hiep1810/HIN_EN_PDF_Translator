import fitz
print("Attributes in fitz matching 'FLAG':")
for x in dir(fitz):
    if "FLAG" in x:
        print(f"{x}: {getattr(fitz, x)}")

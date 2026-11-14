import re, sys
path = sys.argv[1]
lines = open(path).read().split("\n")
i = 0; cur = None; bad = 0
while i < len(lines):
    m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[i])
    if lines[i].startswith("+++ "): cur = lines[i][6:]
    if m:
        old_n = int(m.group(2) or 1); new_n = int(m.group(4) or 1)
        o = n = 0; j = i + 1
        while j < len(lines) and not lines[j].startswith(("@@", "diff --git")):
            l = lines[j]
            if l.startswith("+"): n += 1
            elif l.startswith("-"): o += 1
            elif l.startswith(" ") or l == "": 
                if l == "" and (j == len(lines)-1): break
                o += 1; n += 1
            j += 1
        if (o, n) != (old_n, new_n):
            bad += 1
            print(f"{cur}: header -{old_n} +{new_n}  actual -{o} +{n}  ({lines[i]})")
        i = j; continue
    i += 1
print("mismatches:", bad)

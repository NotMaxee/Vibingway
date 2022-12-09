import os

index = dict()

for root, dirs, files in os.walk("."):
    for filename in files:
        file = os.path.join(root, filename)

        if not file.endswith(".py"):
            continue

        with open(file, "r", encoding="utf-8") as f:
            length = f.read().count("\n")

            index[file] = length

total = 0
for file, length in sorted(index.items(), key=lambda t: t[1]):
    print(f"{file} - {length}")
    total += length

print(f"\nTotal: {total}")
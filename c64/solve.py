def decrypt(seed, data):
    res = []
    for d in data:
        b = seed & 1
        seed = seed // 2
        if b == 1: 
            seed = seed ^ 0xb400
        res.append(seed & 0xff ^ d)
    return res

def check(data):
    return len([ch for ch in data if ch < 32 or ch > 127]) == 0

message = "MERRY XMAS YOU FILTHY ANIMAL AND HAPPY NEW YEAR"
print(decrypt(2025, [ord(c) for c in message]))


data = [
    185, 191, 175, 172, 38, 159, 7, 98, 214, 24, 5, 75, 198, 17, 2, 215, 1, 104, 
    70, 193, 29, 2, 208, 134, 173, 191, 56, 112, 62, 206, 137, 167, 209, 48, 253, 
    142, 191, 46, 155, 19, 107, 64, 43, 220, 7, 96, 194
]

i = 0
while True:
    res = decrypt(i, data)

    if (check(res)):
        print(f"{i}   ", end="")
        for c in res:
            print(chr(c), end="")
        print()
        break

    i += 1

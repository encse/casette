raw_data = open('public/input.txt', 'r').readlines()
data = [list(map(int, x.split(","))) for x in raw_data]
freq = [min([40, 80, 110], key=lambda z: abs((x[1] - x[0]) - z)) for x in data]
digits = [{40:0, 80:1, 110:2}[x] for x in freq]
digit_groups = list(zip(*[digits[i::8] for i in range(8)]))
nums = [''.join(list(map(str, x[1:-2]))) for x in digit_groups]
print(''.join(map(chr, list(map(lambda x: int(x, base=3), nums)))))
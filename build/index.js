function generateSample(freq) {
    var sample = [];
    for (let i = 0; i < 72; i++) {
        let n = 5 * (Math.random() - 0.5);
        let d = Math.sin(2 * Math.PI * freq * i / 18000) * 127;
        let v = Math.trunc(n + d);
        let r = Math.max(-128, Math.min(v, 127));
        sample.push(r);
    }
    return sample;
}
function generateDigit(d) {
    return generateSample([1000, 2000, 3000][d]);
}
function decodeDigit(sample) {
    let f = decodeSample(sample);
    return (f == 1000 ? 0 :
        f == 2000 ? 1 :
            2);
}
function decodeSample(sample) {
    var c = 0;
    for (var i = 1; i < sample.length; i++) {
        if (sample[i - 1] <= 0 && sample[i] > 0) {
            c++;
        }
    }
    var res = c * 250;
    if (res <= 1500) {
        return 1000;
    }
    else if (res <= 2500) {
        return 2000;
    }
    else {
        return 3000;
    }
}
function encodeString(st) {
    let digits = [];
    for (let ch of st) {
        digits.push(generateDigit(0));
        let num = ch.charCodeAt(0);
        let pow = 3 * 3 * 3 * 3;
        for (var i = 0; i < 5; i++) {
            var d = Math.trunc(num / pow);
            num = num % pow;
            pow /= 3;
            digits.push(generateDigit(d));
        }
        digits.push(generateDigit(1));
        digits.push(generateDigit(2));
    }
    return digits;
}
function decodeString(samples) {
    let digits = samples.map(decodeDigit);
    let st = "";
    for (let i = 0; i < digits.length; i += 8) {
        st +=
            String.fromCharCode(81 * digits[i + 1] +
                27 * digits[i + 2] +
                9 * digits[i + 3] +
                3 * digits[i + 4] +
                digits[i + 5]);
    }
    return st;
}
let input = encodeString(`Twas the night before Christmas, when all through the house
Not a creature was stirring, not even a mouse...
     
Happy new year to all advent of coders!
`);
for (const line of input) {
    console.log(line.join(","));
}
export {};
//let digits = input.map(decodeDigit);
//console.log((digits as number[]).reduce((a,b) => a + b));
//console.log(decodeString(input));
//# sourceMappingURL=index.js.map
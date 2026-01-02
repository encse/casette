10 input se
20 sys 8192
30 print chr$(5)
40 row=4: col=6: cch=28: gosub 400
50 row=22: col=10: cch=19: gosub 400
60 get a$:if a$="" then goto 60
70 print chr$(147)
80 end

300 data 185,191,175,172,38,159,7,98,214,24,5,75,198,17
310 data 2,215,1,104,70,193,29,2,208,134,173,191,56,112
320 data 62,206,137,167,209,48,253,142,191,46,155,19,107
330 data 64,43,220,7,96,194

400 poke 214,row:poke 211,col:sys 58732
410 for i=1 to cch
420 read enc
430 gosub 500
440 ch=(enc or r)-(enc and r)
450 print chr$(ch);
460 next
470 return

500 rem lfsr16 step
510 hi=int(se/256):lo=se-256*hi
520 b = lo and 1
530 c = hi and 1
540 lo = int(lo/2) + 128*c
550 hi = int(hi/2)
560 if b=1 then hi = (hi or 180) - (hi and 180)
570 r = lo
580 se = 256 * hi + lo
590 return

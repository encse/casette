![image](image.png)

```
(printf '\x00\x50'; cat screen.bin) > screen.prg
(printf '\x00\x60'; cat color.bin) > color.prg
make
python3 ./build.py
```

all:
	acme -f cbm -o player.prg player.asm
	petcat -w2 -o player_bas.prg player.bas 
	exomizer sfx basic player_bas.prg player.prg ./X-Mas_Song.prg color.prg screen.prg -o xmas.prg
clean:
	rm -f *.o music.prg

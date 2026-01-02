all:
	mkdir -p build
	acme -f cbm -o build/player.prg player.asm
	petcat -w2 -o build/player_bas.prg player.bas 
	exomizer sfx basic build/player_bas.prg build/player.prg X-Mas_Song.prg color.prg screen.prg -o build/xmas.prg
clean:
	rm -f *.o music.prg

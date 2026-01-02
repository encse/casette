; Standalone ACME PRG
; Installs IRQ vector to call SID play routine each IRQ
; SID is assumed to already be loaded at sid_init, sid_play

* = $2000                 ; update the sys in player.bas
sid_init = $4000
sid_play = $4006

start:
        lda #$00          ; select first tune (try #$01 if needed)
        jsr sid_init      ; init music

        sei
        lda #<interrupt   ; point IRQ Vector to our custom irq routine
        ldx #>interrupt
        sta $0314         ; store in $0314/$0315
        stx $0315
        cli

        jsr draw_screen
        rts

interrupt:
        jsr sid_play
        ;dec 53280        ; flash border to see we are live
        jmp $EA31         ; do the normal KERNAL interrupt service routine

draw_screen:
        ;lda #$37
        ;sta $01            ; enable I/O

        lda #$00
        sta $D020          ; border color

        lda #$06
        sta $D021          ; background color

        ldx #$00
copy_screen_loop:
        lda $5000,x
        sta $0400,x
        lda $5100,x
        sta $0500,x
        lda $5200,x
        sta $0600,x
        lda $52E8,x        ; 1000 = $03E8 → last page offset $E8
        sta $06E8,x
        lda $6000,x
        sta $D800,x
        lda $6100,x
        sta $D900,x
        lda $6200,x
        sta $DA00,x
        lda $62E8,x        ; 1000 = $03E8 → last page offset $E8
        sta $DAE8,x
        inx
        bne copy_screen_loop
        rts



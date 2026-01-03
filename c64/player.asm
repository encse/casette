
* = $2000                    ; update the sys in player.bas

SCREEN_RAM        = $0400
COLOR_RAM         = $D800
BORDER_COLOR      = $D020
BACKGROUND_COLOR  = $D021

sid_init    = $4000          ; sid assumed to be loaded here
sid_play    = $4006

; Installs IRQ vector to call SID play routine each IRQ and draws the screen
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
        lda #$00
        sta BORDER_COLOR

        lda #$06
        sta BACKGROUND_COLOR

        ; copy screen and color info in 4x250 byte chunks
        ldx #$FA
-       dex

        lda image_chars + 0 * $fa,x
        sta SCREEN_RAM  + 0 * $fa,x

        lda image_chars + 1 * $fa,x
        sta SCREEN_RAM  + 1 * $fa,x
        
        lda image_chars + 2 * $fa,x
        sta SCREEN_RAM  + 2 * $fa,x
        
        lda image_chars + 3 * $fa,x
        sta SCREEN_RAM  + 3 * $fa,x

        lda image_color + 0 * $fa,x
        sta COLOR_RAM   + 0 * $fa,x

        lda image_color + 1 * $fa,x
        sta COLOR_RAM   + 1 * $fa,x

        lda image_color + 2 * $fa,x
        sta COLOR_RAM   + 2 * $fa,x

        lda image_color + 3 * $fa,x
        sta COLOR_RAM   + 3 * $fa,x

        cpx #$00
        bne -
        rts

image_chars:
    !bin "image.bin"
image_color:
    !bin "color.bin"
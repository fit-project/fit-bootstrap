on run argv
    set msg to "Sembra che il certificato di mitmproxy non sia installato." & return & return & ¬
    "Senza questo certificato, FIT Web non può intercettare il traffico HTTPS e quindi non può funzionare. Per questo motivo verrà chiusa." & return & return & ¬
    "Per installarlo servono i privilegi di amministratore: ti verrà richiesta la password di root (anche più volte)." & return & return & ¬
    "Questa operazione avviene solo la prima volta."
    set dlg_title to "Installazione certificato mitmproxy"
    set cancel_label to "Annulla"
    set ok_label to "OK"

    if (count of argv) ≥ 4 then
        set msg to item 1 of argv
        set dlg_title to item 2 of argv
        set cancel_label to item 3 of argv
        set ok_label to item 4 of argv
    end if

    try
        display dialog msg with title dlg_title default answer "" with hidden answer buttons {cancel_label, ok_label} default button ok_label
        set pwd to text returned of result
    on error number -128
        return ""
    end try

    return pwd
end run

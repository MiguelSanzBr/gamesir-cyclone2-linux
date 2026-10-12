"""Interface language: Portuguese source strings are the keys, :data:`EN` holds the English text.

Only the GUI is translated. ``LANG`` is set once by the app at startup (and the window is rebuilt when it changes),
so ``_()`` is evaluated when a widget is built, never at import time.
"""
import os

LANGS = {"pt": "Português (Brasil)", "en": "English"}
LANG = "pt"


def system_lang(env=os.environ):
    """``"pt"`` when the first locale variable that is set (LANGUAGE, LC_ALL, LC_MESSAGES, LANG) is Portuguese."""
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = env.get(name, "").split(":")[0]
        if value:
            return "pt" if value.startswith("pt") else "en"
    return "en"


def _(text):
    return EN.get(text, text) if LANG == "en" else text


EN = {
    # sections (tiles, page titles) and navigation
    "Botões": "Buttons", "Analógicos": "Sticks", "Gatilhos": "Triggers", "Vibração": "Rumble",
    "Giroscópio": "Gyro", "Luzes": "Lights", "Perfil": "Profile", "‹  Início": "‹  Home",
    "Perfil {}": "Profile {}", "Recarregar": "Reload", "Restaurar backup": "Restore backup",
    # catalog: remap targets, gyro, LED zones, presets, standby
    "Padrão": "Default", "Desativar": "Disable", "Desligado": "Off", "Segurar botão": "Hold button",
    "Apertar liga/desliga": "Press to toggle", "Sempre ligado": "Always on", "Analógico esq.": "Left stick",
    "Analógico dir.": "Right stick", "Mira": "Aim", "Inclinação": "Tilt", "Empunhadura esq.": "Left grip",
    "Empunhadura dir.": "Right grip", "Anel esquerdo": "Left ring", "Anel direito": "Right ring",
    "Fluxo": "Flow", "Arco-íris": "Rainbow", "Pulso": "Pulse", "Duelo": "Standoff", "Alarme": "Alarm",
    "Nunca": "Never",
    # skins and home-page callouts
    "Preto": "Black", "Branco": "White", "Rosa": "Pink", "Analógico esquerdo": "Left stick",
    "Analógico direito": "Right stick", "Botões ABXY": "ABXY buttons", "Traseiros L4 / R4": "Paddles L4 / R4",
    # home
    "Aperte os botões do controle: eles acendem aqui.": "Press the controller's buttons: they light up here.",
    "procurando controle…": "looking for controller…",
    "Perfil ativo no controle: {}": "Active profile on the controller: {}",
    # buttons page
    "Clique num botão do controle para escolher a função dele.\n"
    "L4/R4: botões traseiros · ● verde: botão personalizado.":
        "Click a controller button to choose its function.\nL4/R4: back buttons · green ●: customized button.",
    "Turbo (disparo automático)": "Turbo (auto fire)",
    "Disparo contínuo (aperta uma vez, segura)": "Toggle (press once to hold)",
    "Restaurar todos os botões": "Reset all buttons", "Botão {}": "Button {}",
    "função atual: {}": "current function: {}", "padrão ({})": "default ({})",
    # sticks
    "Zona morta interna": "Inner dead zone", "Zona morta externa (alcance máximo)": "Outer dead zone (max range)",
    "Anti-zona morta": "Anti-dead zone", "Inverter eixo X": "Invert X axis", "Inverter eixo Y": "Invert Y axis",
    "Saída bruta (ignora zona morta e curva)": "Raw output (ignores dead zone and curve)",
    "A zona morta e a curva seguem o modelo do app: os pontos da curva são recalculados quando a zona morta muda.":
        "Dead zone and curve follow the app's model: the curve points are recalculated when the dead zone changes.",
    # triggers
    "Gatilho LT": "LT trigger", "Gatilho RT": "RT trigger", "Início (zona morta)": "Start (dead zone)",
    "Fim (pressão total)": "End (full press)", "Gatilho rápido (hair trigger)": "Hair trigger",
    "Adaptativo": "Adaptive", "Fixo": "Fixed", "Faixa: início": "Range: start", "Faixa: fim": "Range: end",
    # rumble
    "Motores das empunhaduras": "Grip motors", "Motor esquerdo": "Left motor", "Motor direito": "Right motor",
    "Motores dos gatilhos": "Trigger motors", "Teste": "Test", "Vibrar por 1 segundo": "Rumble for 1 second",
    # gyro
    "Ativação": "Activation", "Botão de ativação": "Activation button", "Movimento vira": "Motion controls",
    "Zona morta": "Dead zone", "Proporção X/Y": "X/Y ratio",
    # lights
    "Animação": "Animation", "Animação {}": "Animation {}", "Efeitos prontos": "Presets", "Quadro {}": "Frame {}",
    "Cor": "Color", "Todas": "All", "Brilho e velocidade": "Brightness and speed", "Brilho": "Brightness",
    "Velocidade": "Speed", "Recentes": "Recent",
    "Prévia ao vivo das luzes. Clique numa luz do desenho para pintá-la.":
        "Live light preview. Click a light on the drawing to paint it.",
    "Este modelo acende só as barras das empunhaduras.": "This model only lights the grip bars.",
    # profile page
    "Perfil selecionado": "Selected profile", "Nome": "Name", "Travar diagonais do D-pad": "Lock D-pad diagonals",
    "Trocar A/B e X/Y no modo XInput": "Swap A/B and X/Y in XInput mode",
    "Trocar A/B e X/Y no modo Switch": "Swap A/B and X/Y in Switch mode",
    "Restaurar padrões deste perfil": "Reset this profile to defaults", "Controle": "Controller",
    "Desligar as luzes sem uso após": "Turn off idle lights after",
    "Acordar ao levantar o controle": "Wake when the controller is lifted", "Cor do desenho": "Drawing color",
    "Idioma da interface": "Interface language",
    # status line, connection pill, dialogs
    "Padrões do app restaurados neste perfil.": "App defaults restored for this profile.",
    "controle não encontrado": "controller not found", "Erro": "Error",
    "Conectado · {} · firmware {}": "Connected · {} · firmware {}", "Bateria: {}%": "Battery: {}%",
    "Dispositivo: {}\nFirmware: {}": "Device: {}\nFirmware: {}",
    "Configuração lida do controle. As mudanças são salvas automaticamente.":
        "Settings read from the controller. Changes are saved automatically.",
    "Lendo do controle…": "Reading from the controller…", "Perfil {} ativo.": "Profile {} active.",
    "Trocando para o perfil {}…": "Switching to profile {}…", "Alterações pendentes…": "Pending changes…",
    "verificação falhou: o controle não guardou o que foi enviado":
        "verification failed: the controller did not keep what was sent",
    "✓ Salvo no controle ({} bytes).": "✓ Saved to the controller ({} bytes).",
    "Salvando no controle…": "Saving to the controller…",
    "O controle mudou para o perfil {}.": "The controller switched to profile {}.",
    "Vibrando…": "Rumbling…", "✓ Teste de vibração concluído.": "✓ Rumble test finished.",
    "Fazendo backup…": "Backing up…", "Backup salvo em {}": "Backup saved to {}",
    "Arquivo inválido ({} bytes, esperado {}).": "Invalid file ({} bytes, expected {}).",
    "Restaurar": "Restore", "Substituir todos os perfis e as luzes por este backup?":
        "Replace all profiles and lights with this backup?",
    "verificação falhou": "verification failed", "Backup restaurado e verificado.": "Backup restored and verified.",
    "Restaurando…": "Restoring…",
}

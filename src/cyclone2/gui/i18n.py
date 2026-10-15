"""Interface language: Portuguese source strings are the keys, :data:`EN` and :data:`FR` hold the translations.

Only the GUI is translated. ``LANG`` is set once by the app at startup (and the window is rebuilt when it changes),
so ``_()`` is evaluated when a widget is built, never at import time.
"""
import os

LANGS = {"pt": "Português (Brasil)", "en": "English", "fr": "Français"}
LANG = "pt"


def system_lang(env=os.environ):
    """Language of the first locale variable that is set (LANGUAGE, LC_ALL, LC_MESSAGES, LANG): ``"pt"``, ``"fr"``
    or ``"en"`` (also the fallback for any other language)."""
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = env.get(name, "").split(":")[0]
        if value:
            return next((code for code in ("pt", "fr") if value.startswith(code)), "en")
    return "en"


def _(text):
    """Translation of ``text``; a language without that entry falls back to English, never to the Portuguese source."""
    if LANG == "pt":
        return text
    return TABLES.get(LANG, EN).get(text) or EN.get(text, text)


EN = {
    # sections (tiles, page titles) and navigation
    "Botões": "Buttons", "Analógicos": "Sticks", "Gatilhos": "Triggers", "Vibração": "Rumble",
    "Giroscópio": "Gyro", "Luzes": "Lights", "Perfil": "Profile", "‹  Início": "‹  Home",
    "Perfil {}": "Profile {}", "Recarregar": "Reload", "Restaurar backup": "Restore backup",
    # catalog: remap targets, gyro, LED zones, presets, standby
    "Padrão": "Default", "Desativar": "Disable", "Menu rápido Steam": "Steam quick menu",
    "Desligado": "Off", "Segurar botão": "Hold button",
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
    "Controle GameSir Cyclone 2 não encontrado. Conecte-o com o cabo ou o dongle 2.4G.":
        "GameSir Cyclone 2 not found. Plug it in with the cable or the 2.4G dongle.",
    "O controle não respondeu. Verifique se ele está ligado e conectado (cabo ou dongle 2.4G) e tente de novo.":
        "The controller did not answer. Check that it is on and connected (cable or 2.4G dongle) and try again.",
    "Sem permissão para acessar o controle ({}). Instale a regra udev (veja o README).":
        "No permission to access the controller ({}). Install the udev rule (see the README).", "Erro": "Error",
    "Bateria: {}%": "Battery: {}%",
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
    "Restaurar": "Restore", "Fechar": "Close", "Sim": "Yes", "Não": "No", "Substituir todos os perfis e as luzes por este backup?":
        "Replace all profiles and lights with this backup?",
    "verificação falhou": "verification failed", "Backup restaurado e verificado.": "Backup restored and verified.",
    "Restaurando…": "Restoring…",
}

FR = {
    'Botões': 'Boutons',
    'Analógicos': 'Joysticks',
    'Gatilhos': 'Gâchettes',
    'Vibração': 'Vibration',
    'Giroscópio': 'Gyroscope',
    'Luzes': 'Lumières',
    'Perfil': 'Profil',
    '‹  Início': '‹  Accueil',
    'Perfil {}': 'Profil {}',
    'Recarregar': 'Recharger',
    'Restaurar backup': 'Restaurer la sauvegarde',
    'Padrão': 'Par défaut',
    'Desativar': 'Désactiver',
    'Menu rápido Steam': 'Menu rapide Steam',
    'Desligado': 'Désactivé',
    'Segurar botão': 'Maintenir le bouton',
    'Apertar liga/desliga': 'Appuyer pour activer/désactiver',
    'Sempre ligado': 'Toujours activé',
    'Analógico esq.': 'Joystick gauche',
    'Analógico dir.': 'Joystick droit',
    'Mira': 'Visée',
    'Inclinação': 'Inclinaison',
    'Empunhadura esq.': 'Poignée gauche',
    'Empunhadura dir.': 'Poignée droite',
    'Anel esquerdo': 'Anneau gauche',
    'Anel direito': 'Anneau droit',
    'Fluxo': 'Flux',
    'Arco-íris': 'Arc-en-ciel',
    'Pulso': 'Pulsation',
    'Duelo': 'Duel',
    'Alarme': 'Alarme',
    'Nunca': 'Jamais',
    'Preto': 'Noir',
    'Branco': 'Blanc',
    'Rosa': 'Rose',
    'Analógico esquerdo': 'Joystick gauche',
    'Analógico direito': 'Joystick droit',
    'Botões ABXY': 'Boutons ABXY',
    'Traseiros L4 / R4': 'Palettes L4 / R4',
    'Aperte os botões do controle: eles acendem aqui.': "Appuyez sur les boutons de la manette : ils s'allument ici.",
    'Perfil ativo no controle: {}': 'Profil actif sur la manette : {}',
    'Clique num botão do controle para escolher a função dele.\nL4/R4: botões traseiros · ● verde: botão personalizado.': 'Cliquez sur un bouton de la manette pour choisir sa fonction.\nL4/R4 : boutons arrière · ● vert : bouton personnalisé.',
    'Turbo (disparo automático)': 'Turbo (tir automatique)',
    'Disparo contínuo (aperta uma vez, segura)': 'Bascule (appuyer une fois pour maintenir)',
    'Restaurar todos os botões': 'Réinitialiser tous les boutons',
    'Botão {}': 'Bouton {}',
    'função atual: {}': 'fonction actuelle : {}',
    'padrão ({})': 'par défaut ({})',
    'Zona morta interna': 'Zone morte intérieure',
    'Zona morta externa (alcance máximo)': 'Zone morte extérieure (portée maximale)',
    'Anti-zona morta': 'Anti-zone morte',
    'Inverter eixo X': "Inverser l'axe X",
    'Inverter eixo Y': "Inverser l'axe Y",
    'Saída bruta (ignora zona morta e curva)': 'Sortie brute (ignore la zone morte et la courbe)',
    'A zona morta e a curva seguem o modelo do app: os pontos da curva são recalculados quando a zona morta muda.': "La zone morte et la courbe suivent le modèle de l'appli : les points de la courbe sont recalculés quand la zone morte change.",
    'Gatilho LT': 'Gâchette LT',
    'Gatilho RT': 'Gâchette RT',
    'Início (zona morta)': 'Début (zone morte)',
    'Fim (pressão total)': 'Fin (appui complet)',
    'Gatilho rápido (hair trigger)': 'Gâchette rapide (hair trigger)',
    'Adaptativo': 'Adaptatif',
    'Fixo': 'Fixe',
    'Faixa: início': 'Plage : début',
    'Faixa: fim': 'Plage : fin',
    'Motores das empunhaduras': 'Moteurs des poignées',
    'Motor esquerdo': 'Moteur gauche',
    'Motor direito': 'Moteur droit',
    'Motores dos gatilhos': 'Moteurs des gâchettes',
    'Teste': 'Test',
    'Vibrar por 1 segundo': 'Vibrer pendant 1 seconde',
    'Ativação': 'Activation',
    'Botão de ativação': "Bouton d'activation",
    'Movimento vira': 'Le mouvement pilote',
    'Zona morta': 'Zone morte',
    'Proporção X/Y': 'Ratio X/Y',
    'Animação': 'Animation',
    'Animação {}': 'Animation {}',
    'Efeitos prontos': 'Effets prédéfinis',
    'Quadro {}': 'Image {}',
    'Cor': 'Couleur',
    'Todas': 'Toutes',
    'Brilho e velocidade': 'Luminosité et vitesse',
    'Brilho': 'Luminosité',
    'Velocidade': 'Vitesse',
    'Recentes': 'Récentes',
    'Prévia ao vivo das luzes. Clique numa luz do desenho para pintá-la.': 'Aperçu en direct des lumières. Cliquez sur une lumière du dessin pour la peindre.',
    'Este modelo acende só as barras das empunhaduras.': "Ce modèle n'allume que les barres des poignées.",
    'Perfil selecionado': 'Profil sélectionné',
    'Nome': 'Nom',
    'Travar diagonais do D-pad': 'Verrouiller les diagonales du D-pad',
    'Trocar A/B e X/Y no modo XInput': 'Échanger A/B et X/Y en mode XInput',
    'Trocar A/B e X/Y no modo Switch': 'Échanger A/B et X/Y en mode Switch',
    'Restaurar padrões deste perfil': 'Réinitialiser les valeurs par défaut de ce profil',
    'Controle': 'Manette',
    'Desligar as luzes sem uso após': 'Éteindre les lumières inutilisées après',
    'Acordar ao levantar o controle': 'Réveiller en soulevant la manette',
    'Cor do desenho': 'Couleur du dessin',
    'Idioma da interface': "Langue de l'interface",
    'Padrões do app restaurados neste perfil.': "Valeurs par défaut de l'appli restaurées sur ce profil.",
    'Controle GameSir Cyclone 2 não encontrado. Conecte-o com o cabo ou o dongle 2.4G.': 'GameSir Cyclone 2 introuvable. Branchez-la avec le câble ou le dongle 2,4 G.',
    'O controle não respondeu. Verifique se ele está ligado e conectado (cabo ou dongle 2.4G) e tente de novo.': "La manette n'a pas répondu. Vérifiez qu'elle est allumée et connectée (câble ou dongle 2,4 G), puis réessayez.",
    'Sem permissão para acessar o controle ({}). Instale a regra udev (veja o README).': "Pas d'autorisation pour accéder à la manette ({}). Installez la règle udev (voir le README).",
    'Erro': 'Erreur',
    'Bateria: {}%': 'Batterie : {} %',
    'Dispositivo: {}\nFirmware: {}': 'Appareil : {}\nFirmware : {}',
    'Configuração lida do controle. As mudanças são salvas automaticamente.': 'Configuration lue depuis la manette. Les modifications sont enregistrées automatiquement.',
    'Lendo do controle…': 'Lecture depuis la manette…',
    'Perfil {} ativo.': 'Profil {} actif.',
    'Trocando para o perfil {}…': 'Passage au profil {}…',
    'Alterações pendentes…': 'Modifications en attente…',
    'verificação falhou: o controle não guardou o que foi enviado': "échec de la vérification : la manette n'a pas conservé ce qui a été envoyé",
    '✓ Salvo no controle ({} bytes).': '✓ Enregistré sur la manette ({} octets).',
    'Salvando no controle…': 'Enregistrement sur la manette…',
    'O controle mudou para o perfil {}.': 'La manette est passée au profil {}.',
    'Vibrando…': 'Vibration en cours…',
    '✓ Teste de vibração concluído.': '✓ Test de vibration terminé.',
    'Fazendo backup…': 'Sauvegarde en cours…',
    'Backup salvo em {}': 'Sauvegarde enregistrée dans {}',
    'Arquivo inválido ({} bytes, esperado {}).': 'Fichier invalide ({} octets, {} attendus).',
    'Restaurar': 'Restaurer',
    'Fechar': 'Fermer',
    'Sim': 'Oui',
    'Não': 'Non',
    'Substituir todos os perfis e as luzes por este backup?': 'Remplacer tous les profils et les lumières par cette sauvegarde ?',
    'verificação falhou': 'échec de la vérification',
    'Backup restaurado e verificado.': 'Sauvegarde restaurée et vérifiée.',
    'Restaurando…': 'Restauration…',
}

TABLES = {"en": EN, "fr": FR}

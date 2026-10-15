"""Vocabulary of the interface: sections, remap targets, gyro options, LED zones and their labels."""
from .. import keys

SECTIONS = [("Botões", "buttons"), ("Analógicos", "sticks"), ("Gatilhos", "triggers"), ("Vibração", "rumble"),
            ("Giroscópio", "gyro"), ("Luzes", "leds"), ("Perfil", "profile")]

# every button the drawing shows and the profile stores
BUTTONS = keys.BUTTONS + keys.PADDLES + keys.TRIGGERS
# remap choices: "" keeps the button's own function; "None" disables it
# combination ("+" joins up to 3 keys sent together): Ctrl+2 opens Steam's right-hand quick access menu
SHORTCUTS = [("KB_LCTRL+KB_2", "Menu rápido Steam")]
TARGETS = ([("", "Padrão")] + [(k, k) for k in keys.TARGETS if k != "None"] + SHORTCUTS
           + [("None", "Desativar")])

# gyro: what turns it on, what it moves
ACTIVATION = [(0, "Desligado"), (1, "Segurar botão"), (2, "Apertar liga/desliga"), (3, "Sempre ligado")]
OUTPUTS = [(1, "Analógico esq."), (2, "Analógico dir."), (4, "Mouse")]
GYRO_KEYS = ["LT", "RT", "LB", "RB", "LS", "RS", "L4", "R4", "A", "B", "X", "Y"]
MOTION = [("aim", "Mira"), ("tilt", "Inclinação")]

# LED zones of the lighting record, in the order the editor lists them
ZONES = [("lower_left", "Empunhadura esq."), ("lower_right", "Empunhadura dir."),
         ("upper_left", "Anel esquerdo"), ("upper_right", "Anel direito"), ("home", "Home")]
PRESETS = [("Flow", "Fluxo"), ("Rainbow", "Arco-íris"), ("Pulse", "Pulso"), ("Standoff", "Duelo"),
           ("Alarm", "Alarme"), ("Disable", "Desligado")]
STANDBY = [(0, "Nunca"), (1, "1 min"), (5, "5 min"), (10, "10 min"), (20, "20 min")]
MOTOR_LEVELS = (0, 25, 50, 75, 100)

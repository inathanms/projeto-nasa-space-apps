# REQ-513: qualquer mudança que altere os pixels de saída (stretch, máscara, reprojeção,
# stack, upscale, colormap, defaults) EXIGE incrementar esta constante (mudou pixel => incrementar).
# Ela entra na chave do cache; sem o incremento, imagens antigas continuariam sendo servidas.
RENDER_VERSION = "r1"

# Kevin Briceño (15-11661)

# Constantes del problema
X, Y, Z = 6, 6, 1
T_SIZE = 4
BASE_ADDR = 0

# Definición de límites
L1, U1 = min(X,Y), max(X,Y)+1      
L2, U2 = min(X,Z), max(X,Z)+1
L3, U3 = min(Y,Z), max(Y,Z)+1

# Tamaños de las dimensiones
N1 = U1 - L1 + 1
N2 = U2 - L2 + 1
N3 = U3 - L3 + 1

# Índices calculados (División entera)
I = (L1 + U1) // 2
J = (L2 + U2) // 2
K = (L3 + U3) // 2

print(f"Buscando M[{I}][{J}][{K}]")
print(f"Dimensiones: N_1={N1}, N_2={N2}, N_3={N3}")

# (a) Cálculo en Row-Major (Orden por Filas)
offset_row = ((I - L1) * N2 * N3) + ((J - L2) * N3) + (K - L3)
address_row = BASE_ADDR + (offset_row * T_SIZE)

# (b) Cálculo en Column-Major (Orden por Columnas)
offset_col = (I - L1) + ((J - L2) * N1) + ((K - L3) * N1 * N2)
address_col = BASE_ADDR + (offset_col * T_SIZE)

#Impresion de Resultados:
print(f"Dirección Row-Major: {address_row}")     # Salida: 96
print(f"Dirección Column-Major: {address_col}")  # Salida: 192
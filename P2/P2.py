# Kevin Briceño (15-11661)

import sys

# --- LÓGICA DEL SIMULADOR ---

class DataType:
    def __init__(self, name, alignment):
        self.name = name
        self.alignment = alignment

    def get_size(self):
        raise NotImplementedError

class AtomicType(DataType):
    def __init__(self, name, size, alignment):
        super().__init__(name, alignment)
        self.size = size

    def get_size(self):
        return self.size

class StructType(DataType):
    def __init__(self, name, fields):
        # fields es una lista de objetos DataType
        # La alineación de un struct es la máxima alineación de sus campos
        align = max([f.alignment for f in fields]) if fields else 1
        super().__init__(name, align)
        self.fields = fields

    def calculate_layout(self, strategy="default"):
        """
        Retorna (tamaño_total, desperdicio, detalle_offsets)
        Estrategias: 'default', 'packed', 'optimal'
        """
        current_fields = list(self.fields)
        
        # Estrategia Óptima: Reordenar por alineación descendente
        if strategy == "optimal":
            current_fields.sort(key=lambda x: x.alignment, reverse=True)

        current_offset = 0
        total_waste = 0
        
        for field in current_fields:
            # Estrategia Empaquetada: Alineación siempre es 1 (sin padding)
            req_align = 1 if strategy == "packed" else field.alignment
            
            # Calcular padding necesario
            padding = (req_align - (current_offset % req_align)) % req_align
            
            # Sumar al desperdicio
            total_waste += padding
            current_offset += padding
            
            # Avanzar offset por el tamaño del campo
            # Nota: Si el campo es un Struct, su tamaño ya incluye su propio padding interno
            field_size = field.get_size() if strategy != "packed" else self._get_packed_size(field)
            current_offset += field_size

        # Padding final: El struct completo debe terminar en un múltiplo de su alineación
        struct_align = 1 if strategy == "packed" else self.alignment
        final_padding = (struct_align - (current_offset % struct_align)) % struct_align
        
        total_waste += final_padding
        total_size = current_offset + final_padding
        
        return total_size, total_waste

    def _get_packed_size(self, field):
        # Helper para obtener el tamaño "puro" de un campo anidado si fuera packed
        if isinstance(field, StructType):
            s, _, = field.calculate_layout("packed")
            return s
        return field.get_size()

    def get_size(self):
        # Tamaño por defecto (sin empaquetar)
        s, _ = self.calculate_layout("default")
        return s

class UnionType(DataType):
    def __init__(self, name, fields):
        # Alineación de Union = Máxima alineación de sus campos
        align = max([f.alignment for f in fields]) if fields else 1
        super().__init__(name, align)
        self.fields = fields

    def get_size(self):
        # Tamaño de Union = Máximo tamaño de sus campos (rellenado para cumplir alineación)
        if not self.fields: return 0
        max_size = max([f.get_size() for f in self.fields])
        
        # El tamaño final debe ser múltiplo de la alineación
        padding = (self.alignment - (max_size % self.alignment)) % self.alignment
        return max_size + padding

    def describe_union(self):
        # Para unions, las estrategias de reordenamiento no aplican igual,
        # pero el tamaño siempre es el del mayor componente.
        size = self.get_size()
        # En una union, el "desperdicio" es relativo al campo activo, 
        # pero definiremos desperdicio como (SizeUnion - SizeCampo) promedio o max.
        # retornaremos el tamaño fijo.
        return size

# --- GESTOR DE TIPOS Y REPL ---

class TypeManager:
    def __init__(self):
        self.registry = {}

    def register_atomic(self, name, size, align):
        if size <= 0 or align <= 0:
            return "Error: Tamaño y alineación deben ser positivos."

        self.registry[name] = AtomicType(name, size, align)
        return f"Definido ATOMICO {name}"

    def register_struct(self, name, type_names):
        fields = []
        for t_name in type_names:
            if t_name not in self.registry:
                return f"Error: Tipo '{t_name}' no definido."
            fields.append(self.registry[t_name])
        
        self.registry[name] = StructType(name, fields)
        return f"Definido STRUCT {name}"

    def register_union(self, name, type_names):
        fields = []
        for t_name in type_names:
            if t_name not in self.registry:
                return f"Error: Tipo '{t_name}' no definido."
            fields.append(self.registry[t_name])
        
        self.registry[name] = UnionType(name, fields)
        return f"Definido UNION {name}"

    def describe(self, name):
        if name not in self.registry:
            return f"Error: Tipo '{name}' no encontrado."
        
        dtype = self.registry[name]
        output = []
        output.append(f"Tipo: {name} ({dtype.__class__.__name__})")
        
        if isinstance(dtype, AtomicType):
            output.append(f"  Tamaño: {dtype.get_size()}")
            output.append(f"  Alineación: {dtype.alignment}")
        
        elif isinstance(dtype, UnionType):
            output.append(f"  Tamaño: {dtype.get_size()}")
            output.append(f"  Alineación: {dtype.alignment}")
            output.append("  (Nota: En Unions el espacio se solapa)")

        elif isinstance(dtype, StructType):
            # Estrategia 1: Sin empaquetar
            s_def, w_def = dtype.calculate_layout("default")
            output.append(f"  [Sin empaquetar] Tamaño: {s_def}, Desperdicio: {w_def}")
            
            # Estrategia 2: Empaquetado
            s_pack, w_pack = dtype.calculate_layout("packed")
            output.append(f"  [Empaquetado]    Tamaño: {s_pack}, Desperdicio: {w_pack}")
            
            # Estrategia 3: Óptimo
            s_opt, w_opt = dtype.calculate_layout("optimal")
            output.append(f"  [Reordenado]     Tamaño: {s_opt}, Desperdicio: {w_opt}")

        return "\n".join(output)

# --- INTERFAZ DE USUARIO ---
def main():
    
    manager = TypeManager()
    print("Simulador de Tipos (Escribe 'SALIR' para terminar)")
    
    while True:
        try:
            line = input("> ").strip().split()
            if not line: continue
            
            cmd = line[0].upper()
            
            if cmd == "SALIR":
                break
                
            elif cmd == "ATOMICO":
                # Sintaxis: ATOMICO <nombre> <size> <align>
                if len(line) != 4:
                    print("Uso: ATOMICO <nombre> <size> <align>")
                    continue
                name, size, align = line[1], int(line[2]), int(line[3])
                print(manager.register_atomic(name, size, align))
                
            elif cmd == "STRUCT":
                # Sintaxis: STRUCT <nombre> <tipo1> <tipo2> ...
                if len(line) < 3:
                    print("Uso: STRUCT <nombre> <tipo> ...")
                    continue
                name = line[1]
                types = line[2:]
                print(manager.register_struct(name, types))

            elif cmd == "UNION":
                # Sintaxis: UNION <nombre> <tipo1> <tipo2> ...
                if len(line) < 3:
                    print("Uso: UNION <nombre> <tipo> ...")
                    continue
                name = line[1]
                types = line[2:]
                print(manager.register_union(name, types))

            elif cmd == "DESCRIBIR":
                if len(line) != 2:
                    print("Uso: DESCRIBIR <nombre>")
                    continue
                print(manager.describe(line[1]))
            
            else:
                print("Comando desconocido.")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()

# Kevin Briceño (15-11661)

import unittest
from unittest.mock import patch
from io import StringIO
import sys

# Importamos las clases desde P2
from P2 import TypeManager, DataType, AtomicType, StructType, UnionType, main

class TestTypeManager(unittest.TestCase):
    def setUp(self):
        self.tm = TypeManager()
        self.tm.register_atomic("char", 1, 1)
        self.tm.register_atomic("int", 4, 4)
        self.tm.register_atomic("double", 8, 8)

    # --- PRUEBAS DE LÓGICA ---
    def test_atomic(self):
        desc = self.tm.describe("int")
        self.assertIn("Tamaño: 4", desc)
        self.assertIn("Alineación: 4", desc)

    def test_struct_simple_padding(self):
        # Caso clásico: char(1) + pad(3) + int(4) = 8
        self.tm.register_struct("test1", ["char", "int"])
        t = self.tm.registry["test1"]
        s, w = t.calculate_layout("default")
        self.assertEqual(s, 8)
        self.assertEqual(w, 3)

    def test_struct_optimal(self):
        # Default: char(1)+pad(7) + double(8) + char(1)+pad(7) = 24
        # Optimal: double(8) + char(1) + char(1) + pad(6) = 16
        self.tm.register_struct("test2", ["char", "double", "char"])
        t = self.tm.registry["test2"]
        s_def, _ = t.calculate_layout("default")
        s_opt, _ = t.calculate_layout("optimal")
        self.assertEqual(s_def, 24)
        self.assertEqual(s_opt, 16)

    def test_union_simple(self):
        # Union max(char 1, double 8) = 8
        self.tm.register_union("u1", ["char", "double"])
        t = self.tm.registry["u1"]
        self.assertEqual(t.get_size(), 8)
        self.assertIn("se solapa", self.tm.describe("u1"))
    
    def test_nested_structs_packed(self):
        # Probamos _get_packed_size recursivo
        self.tm.register_struct("inner", ["char", "int"]) # size 8 (def), 5 (pack)
        self.tm.register_struct("outer", ["char", "inner"]) 
        t = self.tm.registry["outer"]
        # packed: char(1) + inner(5) = 6
        s_pack, w_pack = t.calculate_layout("packed")
        self.assertEqual(s_pack, 6)
        self.assertEqual(w_pack, 0)
    
    def test_empty_union(self):
        # Cubre la línea: if not self.fields: return 0
        u = UnionType("vacio", [])
        self.assertEqual(u.get_size(), 0)

    # --- PRUEBAS DE ERRORES Y CLASES ABSTRACTAS ---
    
    def test_abstract_class_error(self):
        # Cubre la línea 11: raise NotImplementedError
        dt = DataType("abstracto", 1)
        with self.assertRaises(NotImplementedError):
            dt.get_size()
    
    def test_register_errors(self):
        # Cubre líneas 152-163: Tipos no definidos
        res = self.tm.register_struct("fallo", ["char", "fantasma"])
        self.assertIn("Error", res)
        self.assertIn("no definido", res)

        res = self.tm.register_union("fallo_u", ["fantasma"])
        self.assertIn("Error", res)

        # Validación de atómicos (si agregaste el fix anterior)
        res = self.tm.register_atomic("bad", 0, -5)
        self.assertIn("Error", res)

    def test_nested_structs(self):
        # Struct interno: char(1) + pad(3) + int(4) = 8 bytes. Alineación 4.
        self.tm.register_struct("inner", ["char", "int"])
        
        # Struct externo: char(1) + pad(3) + inner(8) = 12 bytes.
        self.tm.register_struct("outer", ["char", "inner"])
        
        t = self.tm.registry["outer"]
        s, w = t.calculate_layout("default")
        
        # Explicación: 
        # offset 0: char (1)
        # offset 1: padding (3) para llegar a align 4 (requerido por 'inner')
        # offset 4: inner struct (8)
        # Total: 12 bytes.
        self.assertEqual(s, 12)
        self.assertEqual(w, 3) # Solo 3 bytes de padding explícito en 'outer'

    def test_struct_with_union(self):
        # Union (4 bytes, align 4)
        self.tm.register_union("u_int", ["int", "char"])
        # Struct: char(1) + pad(3) + union(4) = 8 bytes
        self.tm.register_struct("s_mix", ["char", "u_int"])
        
        t = self.tm.registry["s_mix"]
        self.assertEqual(t.get_size(), 8)

    def test_error_handling(self):
        # Registrar struct con tipo inexistente
        res = self.tm.register_struct("fail", ["char", "imaginary"])
        self.assertIn("Error", res)
        self.assertIn("imaginary", res)
        
        # Registrar union con tipo inexistente
        res = self.tm.register_union("fail_u", ["imaginary"])
        self.assertIn("Error", res)

        # Describir tipo inexistente
        res = self.tm.describe("ghost")
        self.assertIn("no encontrado", res)

        # Atómico inválido
        res = self.tm.register_atomic("bad", 0, -1)
        self.assertIn("Error", res)

    # --- PRUEBAS DEL MAIN LOOP ---

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_integration(self, mock_stdout, mock_input):
        """
        Simulamos una sesión completa de usuario.
        mock_input.side_effect alimenta al input() del programa línea por línea.
        """
        mock_input.side_effect = [
            "",                     # Línea vacía (debe ignorarla)
            "COMANDO_INVALIDO",      # Comando desconocido
            "ATOMICO byte 1 1",      # Crear atómico
            "ATOMICO short 2 2",
            "STRUCT s1 byte short",  # Crear struct
            "UNION u1 byte short",   # Crear union
            "DESCRIBIR s1",          # Describir
            "DESCRIBIR u1",
            "DESCRIBIR no_existe",   # Error en describir
            "ATOMICO malo 1",        # Argumentos incompletos
            "STRUCT malo",           # Argumentos incompletos
            "UNION malo",            # Argumentos incompletos
            "SALIR"                  # Terminar programa
        ]

        # Ejecutamos el main
        try:
            main()
        except SystemExit:
            pass

        # Verificamos que la salida contenga respuestas esperadas
        output = mock_stdout.getvalue()
        
        self.assertIn("Simulador de Tipos", output)
        self.assertIn("Definido ATOMICO byte", output)
        self.assertIn("Definido STRUCT s1", output)
        self.assertIn("Definido UNION u1", output)
        self.assertIn("Tamaño: 4", output) # s1 size (1 + pad 1 + 2) = 4
        self.assertIn("Comando desconocido", output)
        self.assertIn("Uso: ATOMICO", output)
        self.assertIn("Error: Tipo 'no_existe' no encontrado", output)

if __name__ == "__main__":
    unittest.main()
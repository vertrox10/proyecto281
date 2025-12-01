# jwt_utils.py - Funciones JWT independientes MEJORADO
import jwt as pyjwt
from datetime import datetime, timedelta

# 🔥 CONFIGURACIÓN JWT MANUAL
JWT_SECRET_KEY = 'tu-clave-super-segura-inf281-2025-movil-app-12345'
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DAYS = 365

def create_jwt_token(user_id, correo, id_rol, nombre):
    """Crear token JWT manualmente - VERSIÓN MEJORADA"""
    # ✅ CONVERTIR user_id A STRING (estándar JWT)
    user_id_str = str(user_id)
    
    payload = {
        'sub': user_id_str,  # JWT estándar usa string para 'sub'
        'user_id': user_id,  # ← AGREGAR TAMBIÉN COMO ENTERO POR SI ACASO
        'correo': correo,
        'id_rol': id_rol,
        'nombre': nombre,
        'exp': datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS),
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    
    token = pyjwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    print(f"✅ Token JWT generado para usuario: {user_id} (sub: {user_id_str})")
    return token

def verify_jwt_token(token):
    """Verificar token JWT manualmente - VERSIÓN MEJORADA"""
    try:
        payload = pyjwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # ✅ BUSCAR USER_ID EN MÚLTIPLES CAMPOS
        user_id = None
        
        # Prioridad 1: 'sub' (estándar JWT)
        if 'sub' in payload:
            user_id = payload['sub']
            print(f"✅ Token verificado - User ID desde 'sub': {user_id}")
        
        # Prioridad 2: 'user_id' (campo personalizado)
        elif 'user_id' in payload:
            user_id = payload['user_id']
            print(f"✅ Token verificado - User ID desde 'user_id': {user_id}")
        
        if user_id is None:
            print("❌ Token no contiene user_id")
            return None
            
        return payload
        
    except pyjwt.ExpiredSignatureError:
        print("❌ Token expirado")
        return None
    except pyjwt.InvalidTokenError as e:
        print(f"❌ Token inválido: {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado verificando token: {e}")
        return None
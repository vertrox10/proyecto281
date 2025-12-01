# jwt_decorators.py - Decorators JWT independientes CORREGIDO
from flask import request, jsonify
from functools import wraps
from jwt_utils import verify_jwt_token

def jwt_required(f):
    """Decorator personalizado para verificar JWT - VERSIÓN CORREGIDA"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({"success": False, "message": "Token faltante"}), 401
        
        try:
            # Extraer el token del header "Bearer {token}"
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
            else:
                token = auth_header
            
            print(f"🔐 [JWT_DECORATOR] Verificando token: {token[:50]}...")
            
            # Verificar el token
            payload = verify_jwt_token(token)
            if not payload:
                return jsonify({"success": False, "message": "Token inválido"}), 422
            
            # ✅ OBTENER USER_ID DEL PAYLOAD
            user_id = payload.get('sub')
            if not user_id:
                return jsonify({"success": False, "message": "Token no contiene user_id"}), 422
            
            print(f"🔐 [JWT_DECORATOR] User ID encontrado: {user_id}, Tipo: {type(user_id)}")
            
            # ✅ CORRECCIÓN CRÍTICA: CONVERTIR A ENTERO
            try:
                user_id_int = int(user_id)
                print(f"✅ [JWT_DECORATOR] User ID convertido a entero: {user_id_int}")
            except (ValueError, TypeError) as e:
                print(f"❌ [JWT_DECORATOR] Error convirtiendo user_id a entero: {e}")
                return jsonify({
                    "success": False, 
                    "message": "Formato de user_id inválido"
                }), 422
            
            # ✅ AGREGAR A LA REQUEST COMO ENTERO
            request.jwt_payload = payload
            request.current_user_id = user_id_int  # ← AHORA ES ENTERO
            request.current_user_id_str = user_id  # ← Y TAMBIÉN GUARDAR COMO STRING POR SI ACASO
            request.current_user_role = payload.get('id_rol')
            print(f"✅ [JWT_DECORATOR] Token válido - User ID: {user_id_int} (entero)")
            
        except Exception as e:
            print(f"❌ [JWT_DECORATOR] Error procesando token: {e}")
            return jsonify({"success": False, "message": "Error procesando token"}), 422
        
        return f(*args, **kwargs)
    
    return decorated_function
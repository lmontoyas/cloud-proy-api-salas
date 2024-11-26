import boto3
import json
import os

def lambda_handler(event, context):
    try:
        print(event)

        if isinstance(event['body'], str):
            body = json.loads(event['body'])
        else:
            body = event['body']

        # Extraer valores del cuerpo
        tenant_id = body['tenant_id']
        departamento = body['departamento']
        provincia = body['provincia']
        distrito = body['distrito']
        num_sala = body['num_sala']
        capacidad = body['capacidad']
        tipo = body['tipo']
        estado = body['estado']

        tabla_cines = os.environ["TABLE_NAME_SALAS"]

        if not tenant_id and not departamento and not provincia and not distrito and not num_sala and not capacidad and not tipo and not estado:
            return {
                    'statusCode': 400,
                    'status': 'Bad Request - Faltan datos por completar'
                }

        # Concatenar los valores de pais, departamento y distrito para formar el campo ordenamiento
        sala_id = f"{departamento}#{provincia}#{distrito}#Sala#{num_sala}" 

        # Proteger el Lambda con autenticación de token
        token = event['headers'].get('Authorization', None)
        if not token:
            return {
                'statusCode': 401,
                'status': 'Unauthorized - Falta el token de autorización'
            }

        lambda_name = os.environ.get('LAMBDA_VALIDAR_TOKEN')

        # Validar que token exista y esté vigente
        lambda_client = boto3.client('lambda')
        payload_string = json.dumps(
            {
                "tenant_id": tenant_id,
                "token": token
                })
        
        invoke_response = lambda_client.invoke(
            FunctionName=lambda_name,
            InvocationType='RequestResponse',
            Payload=payload_string
        )
        response = json.loads(invoke_response['Payload'].read())
        print(response)
        if response['statusCode'] == 403:
            return {
                'statusCode': 403,
                'status': 'Forbidden - Acceso NO Autorizado'
            }
        
        # Validar que cine exista previo a la inserción de la sala
        lambda_buscar_cine_name = os.environ.get('LAMBDA_BUSCAR_CINE')

        payload_buscar_cine = json.dumps(
        {
            "tenant_id": tenant_id,
            "departamento": departamento,
            "provincia": provincia,
            "distrito": distrito
        }
        )

        buscar_cine_response = lambda_client.invoke(
            FunctionName=lambda_buscar_cine_name,
            InvocationType='RequestResponse',
            Payload=payload_buscar_cine
        )

        buscar_cine_data = json.loads(buscar_cine_response['Payload'].read())

        # Revisar si el cine existe
        if buscar_cine_data['statusCode'] != 200 or not buscar_cine_data['data']:
            return {
                'statusCode': 404,
                'status': 'Not Found - El cine especificado no existe'
            }

        # Conexión a DynamoDB y creación del nuevo registro
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(tabla_cines)

        # Insertar el nuevo registro en la tabla
        response = table.put_item(
            Item={
                'tenant_id': tenant_id,
                'sala_id': sala_id,
                'capacidad': capacidad,
                'tipo': tipo,
                'estado': estado
            }
        )

        # Respuesta de éxito
        return {
            'statusCode': 201,
            'status': 'Sala creada exitosamente',
            'response': response
        }

    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return {
            'statusCode': 500,
            'status': 'Internal Server Error - Ocurrió un error inesperado'
        }
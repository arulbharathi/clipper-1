# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: spd_frontend.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='spd_frontend.proto',
  package='clipper.grpc',
  syntax='proto3',
  serialized_pb=_b('\n\x12spd_frontend.proto\x12\x0c\x63lipper.grpc\" \n\x0b\x46loatsInput\x12\x11\n\x05input\x18\x01 \x03(\x02\x42\x02\x10\x01\"L\n\x0ePredictRequest\x12)\n\x06inputs\x18\x01 \x03(\x0b\x32\x19.clipper.grpc.FloatsInput\x12\x0f\n\x07msg_ids\x18\x02 \x03(\x05\"\"\n\x0fPredictResponse\x12\x0f\n\x07msg_ids\x18\x01 \x03(\x05\x32Y\n\x07Predict\x12N\n\rPredictFloats\x12\x1c.clipper.grpc.PredictRequest\x1a\x1d.clipper.grpc.PredictResponse\"\x00\x62\x06proto3')
)




_FLOATSINPUT = _descriptor.Descriptor(
  name='FloatsInput',
  full_name='clipper.grpc.FloatsInput',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='input', full_name='clipper.grpc.FloatsInput.input', index=0,
      number=1, type=2, cpp_type=6, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=_descriptor._ParseOptions(descriptor_pb2.FieldOptions(), _b('\020\001')), file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=36,
  serialized_end=68,
)


_PREDICTREQUEST = _descriptor.Descriptor(
  name='PredictRequest',
  full_name='clipper.grpc.PredictRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='inputs', full_name='clipper.grpc.PredictRequest.inputs', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='msg_ids', full_name='clipper.grpc.PredictRequest.msg_ids', index=1,
      number=2, type=5, cpp_type=1, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=70,
  serialized_end=146,
)


_PREDICTRESPONSE = _descriptor.Descriptor(
  name='PredictResponse',
  full_name='clipper.grpc.PredictResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='msg_ids', full_name='clipper.grpc.PredictResponse.msg_ids', index=0,
      number=1, type=5, cpp_type=1, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=148,
  serialized_end=182,
)

_PREDICTREQUEST.fields_by_name['inputs'].message_type = _FLOATSINPUT
DESCRIPTOR.message_types_by_name['FloatsInput'] = _FLOATSINPUT
DESCRIPTOR.message_types_by_name['PredictRequest'] = _PREDICTREQUEST
DESCRIPTOR.message_types_by_name['PredictResponse'] = _PREDICTRESPONSE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

FloatsInput = _reflection.GeneratedProtocolMessageType('FloatsInput', (_message.Message,), dict(
  DESCRIPTOR = _FLOATSINPUT,
  __module__ = 'spd_frontend_pb2'
  # @@protoc_insertion_point(class_scope:clipper.grpc.FloatsInput)
  ))
_sym_db.RegisterMessage(FloatsInput)

PredictRequest = _reflection.GeneratedProtocolMessageType('PredictRequest', (_message.Message,), dict(
  DESCRIPTOR = _PREDICTREQUEST,
  __module__ = 'spd_frontend_pb2'
  # @@protoc_insertion_point(class_scope:clipper.grpc.PredictRequest)
  ))
_sym_db.RegisterMessage(PredictRequest)

PredictResponse = _reflection.GeneratedProtocolMessageType('PredictResponse', (_message.Message,), dict(
  DESCRIPTOR = _PREDICTRESPONSE,
  __module__ = 'spd_frontend_pb2'
  # @@protoc_insertion_point(class_scope:clipper.grpc.PredictResponse)
  ))
_sym_db.RegisterMessage(PredictResponse)


_FLOATSINPUT.fields_by_name['input'].has_options = True
_FLOATSINPUT.fields_by_name['input']._options = _descriptor._ParseOptions(descriptor_pb2.FieldOptions(), _b('\020\001'))

_PREDICT = _descriptor.ServiceDescriptor(
  name='Predict',
  full_name='clipper.grpc.Predict',
  file=DESCRIPTOR,
  index=0,
  options=None,
  serialized_start=184,
  serialized_end=273,
  methods=[
  _descriptor.MethodDescriptor(
    name='PredictFloats',
    full_name='clipper.grpc.Predict.PredictFloats',
    index=0,
    containing_service=None,
    input_type=_PREDICTREQUEST,
    output_type=_PREDICTRESPONSE,
    options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_PREDICT)

DESCRIPTOR.services_by_name['Predict'] = _PREDICT

# @@protoc_insertion_point(module_scope)
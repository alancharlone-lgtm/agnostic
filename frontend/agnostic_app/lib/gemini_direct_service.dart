import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/io.dart';
import 'package:http/http.dart' as http;

/// 🔀 GeminiDirectService — Hybrid Audio Architecture
///
/// Connects Flutter DIRECTLY to Gemini Live API via raw WebSocket for
/// zero-latency audio. No third-party packages required beyond web_socket_channel.
///
/// Tool calls are intercepted here and forwarded to the Python backend via HTTP.
/// Camera frames are attached as Snapshot-on-Demand for vision tools.
///
/// Rollback: Set [_useDirectGemini] to false in main.dart to revert
/// to the original WebSocket relay through Python.
class GeminiDirectService {
  final String backendUrl;

  // Callbacks to main.dart UI
  final Function(Uint8List audioBytes) onAudioReceived;
  final Function(Map<String, dynamic> toolResult, String toolName) onToolExecuted;
  final Function(String text) onLog;
  final Function() onInterrupted;
  final Function(List<double> coords, String label)? onBoundingBox;
  final Function(Uint8List? imgBytes, String? imgUrl, String context)? onVisualGuide;
  final Function(bool on)? onFlashlight;
  final Function(String msg)? onSafetyAlert;
  final Function(List<String> links)? onPartsLinks;  // 🛒 Links de repuestos ML

  // Frame provider — main.dart sets this so we can grab HD snapshots on demand
  Uint8List? Function()? frameProvider;

  // Internal state
  WebSocketChannel? _wsChannel;
  String _userId = 'default';
  bool _isConnected = false;

  // Gemini Live WebSocket base URL
  static const String _geminiWsBase =
      'wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContentConstrained';

  GeminiDirectService({
    required this.backendUrl,
    required this.onAudioReceived,
    required this.onToolExecuted,
    required this.onLog,
    required this.onInterrupted,
    this.onBoundingBox,
    this.onVisualGuide,
    this.onFlashlight,
    this.onSafetyAlert,
    this.onPartsLinks,
    this.frameProvider,
  });

  bool get isConnected => _isConnected;

  // Tools that run LOCALLY in Flutter (no HTTP round-trip needed)
  static const Set<String> _localTools = {
    'control_phone_flashlight',
    'handle_vision_result',
    'start_safety_monitoring',
  };

  // Tools that need a camera frame attached (Snapshot-on-Demand)
  static const Set<String> _visionTools = {
    'mostrar_componente',
    'generar_guia_visual_ensamblaje',
    'evaluacion_paso_a_paso',
    'safety_guardian_agent',
    'consultar_vision_precision',
  };

  /// Step 1: Request ephemeral token from Python backend
  Future<Map<String, dynamic>> _getEphemeralToken(String mode, String location) async {
    onLog('🔐 Requesting ephemeral token...');
    try {
      final resp = await http.get(Uri.parse(
        '$backendUrl/api/ephemeral-token?mode=${Uri.encodeComponent(mode)}&location=${Uri.encodeComponent(location)}'
      )).timeout(const Duration(seconds: 10));

      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body);
        if (data['fallback'] == true) {
          onLog('⚠️ Ephemeral token fallback (using direct key)');
        } else {
          onLog('🔐 Ephemeral token received OK');
        }
        return data;
      } else {
        throw Exception('Token endpoint returned ${resp.statusCode}');
      }
    } catch (e) {
      onLog('❌ Token error: $e');
      rethrow;
    }
  }

  /// Step 2: Connect directly to Gemini Live via raw WebSocket
  Future<void> connect({
    required String mode,
    required String location,
    String userId = 'default',
  }) async {
    _userId = userId;

    try {
      // 1. Get ephemeral token + config from Python backend
      final config = await _getEphemeralToken(mode, location);
      final token = config['token'] as String;
      final systemPrompt = config['system_prompt'] as String;
      final model = config['model'] as String;
      final toolDecls = config['tool_declarations'] as List<dynamic>;

      // 2. Build the Gemini Live WebSocket URL
      // Use access_token query param for authentication
      final tokenValue = token.startsWith('auth_tokens/') ? token.replaceFirst('auth_tokens/', '') : token;
      final wsUrl = Uri.parse('$_geminiWsBase?access_token=$tokenValue');

      // 3. Open WebSocket to Gemini Live
      onLog('🎙️ Connecting directly to Gemini Live (access_token)...');
      _wsChannel = WebSocketChannel.connect(wsUrl);

      // 4. Send the setup message (configures model, tools, system prompt)
      final setupMessage = {
        'setup': {
          'model': 'models/$model',
          'generation_config': {
            'response_modalities': ['AUDIO'],
          },
          'system_instruction': {
            'parts': [{'text': systemPrompt}],
          },
          'tools': toolDecls,
        }
      };
      _wsChannel!.sink.add(jsonEncode(setupMessage));
      onLog('📋 Setup message sent (model: $model)');

      // 5. Listen for messages from Gemini
      _wsChannel!.stream.listen(
        _handleRawMessage,
        onError: (error) {
          onLog('🚨 Gemini WS error: $error');
          _isConnected = false;
        },
        onDone: () {
          final code = _wsChannel?.closeCode;
          final reason = _wsChannel?.closeReason;
          onLog('🚪 Gemini WS closed (Code: $code, Reason: $reason)');
          _isConnected = false;
        },
      );

      _isConnected = true;
      onLog('✅ Direct Gemini Live connection opened!');

    } catch (e) {
      onLog('❌ Direct connection failed: $e');
      _isConnected = false;
      rethrow;
    }
  }

  /// Handle raw WebSocket messages from Gemini Live
  void _handleRawMessage(dynamic rawMessage) {
    try {
      Map<String, dynamic> msg;

      if (rawMessage is String) {
        msg = jsonDecode(rawMessage);
      } else if (rawMessage is Uint8List) {
        // Binary: raw audio from Gemini → pass directly to player
        onAudioReceived(rawMessage);
        return;
      } else {
        return;
      }

      // --- Setup complete confirmation ---
      if (msg.containsKey('setupComplete')) {
        onLog('🟢 Gemini setup complete');
        return;
      }

      // --- Server content (audio, text, interruptions) ---
      final serverContent = msg['serverContent'];
      if (serverContent != null) {
        // Barge-in / interruption
        if (serverContent['interrupted'] == true) {
          onLog('🔇 BARGE-IN detected');
          onInterrupted();
        }

        // Model turn (audio output)
        final modelTurn = serverContent['modelTurn'];
        if (modelTurn != null) {
          final parts = modelTurn['parts'] as List<dynamic>?;
          if (parts != null) {
            for (final part in parts) {
              // Inline audio data (base64 PCM)
              final inlineData = part['inlineData'];
              if (inlineData != null && inlineData['data'] != null) {
                final audioBytes = base64Decode(inlineData['data']);
                onAudioReceived(Uint8List.fromList(audioBytes));
              }
              // Text output
              final text = part['text'];
              if (text != null) {
                debugPrint('GEMINI DIRECT TEXT: $text');
              }
            }
          }
        }

        // Turn complete
        if (serverContent['turnComplete'] == true) {
          debugPrint('GEMINI DIRECT: Turn complete');
        }
      }

      // --- Tool calls ---
      final toolCall = msg['toolCall'];
      if (toolCall != null) {
        _handleToolCalls(toolCall);
      }

    } catch (e) {
      debugPrint('Error parsing Gemini message: $e');
    }
  }

  /// Process tool calls from Gemini
  Future<void> _handleToolCalls(Map<String, dynamic> toolCall) async {
    final functionCalls = toolCall['functionCalls'] as List<dynamic>?;
    if (functionCalls == null) return;

    for (final call in functionCalls) {
      final name = call['name'] as String? ?? 'unknown';
      final args = Map<String, dynamic>.from(call['args'] ?? {});
      final id = call['id'] as String? ?? '';

      onLog('🔧 Tool call: $name');

      try {
        Map<String, dynamic> result;

        if (_localTools.contains(name)) {
          result = await _executeLocalTool(name, args);
        } else {
          result = await _executeRemoteTool(name, args);
        }

        // Send result back to Gemini via WebSocket
        final response = {
          'toolResponse': {
            'functionResponses': [{
              'id': id,
              'name': name,
              'response': result,
            }]
          }
        };
        _wsChannel?.sink.add(jsonEncode(response));

        onToolExecuted(result, name);
        _handleToolResultUI(name, result);

      } catch (e) {
        onLog('❌ Tool $name failed: $e');

        final errorResponse = {
          'toolResponse': {
            'functionResponses': [{
              'id': id,
              'name': name,
              'response': {'error': e.toString(), 'message': 'Tool execution failed.'},
            }]
          }
        };
        _wsChannel?.sink.add(jsonEncode(errorResponse));
      }
    }
  }

  /// Execute tools that run locally in Flutter
  Future<Map<String, dynamic>> _executeLocalTool(String name, Map<String, dynamic> args) async {
    switch (name) {
      case 'control_phone_flashlight':
        final action = args['action'] as String? ?? 'off';
        final on = action.toLowerCase() == 'on';
        onFlashlight?.call(on);
        onLog('🔦 Flashlight ${on ? "ON" : "OFF"} (local)');
        return {'status': 'ok', 'action': action};

      case 'handle_vision_result':
        onLog('👁️ Vision result stored (local)');
        return {'status': 'stored', 'message': 'Result saved locally.'};

      case 'start_safety_monitoring':
        onLog('🛡️ Safety monitoring (passive)');
        return {
          'status': 'monitoring_passive',
          'message': 'Vigilancia en modo pasivo.',
        };

      default:
        return {'error': 'Unknown local tool: $name'};
    }
  }

  /// Execute tools on the Python backend via HTTP (Snapshot-on-Demand)
  Future<Map<String, dynamic>> _executeRemoteTool(String name, Map<String, dynamic> args) async {
    onLog('🌐 $name → Python backend...');

    // 📷 Snapshot-on-Demand: capture HD frame at the EXACT moment of the tool call
    String? frameB64;
    if (_visionTools.contains(name) && frameProvider != null) {
      final frame = frameProvider!();
      if (frame != null) {
        frameB64 = base64Encode(frame);
        onLog('📷 Snapshot attached (${frame.length} bytes)');
      }
    }

    try {
      final resp = await http.post(
        Uri.parse('$backendUrl/api/execute-tool'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': name,
          'args': args,
          'user_id': _userId,
          'frame_base64': frameB64,
        }),
      ).timeout(const Duration(seconds: 60));

      if (resp.statusCode == 200) {
        final result = jsonDecode(resp.body) as Map<String, dynamic>;
        final durationMs = result['_duration_ms'] ?? 0;
        onLog('✅ $name completed (${durationMs}ms)');
        return result;
      } else {
        throw Exception('HTTP ${resp.statusCode}: ${resp.body}');
      }
    } catch (e) {
      onLog('❌ Remote tool $name failed: $e');
      rethrow;
    }
  }

  /// Handle tool results for UI updates
  void _handleToolResultUI(String name, Map<String, dynamic> result) {
    if (result.containsKey('error')) return;

    switch (name) {
      case 'mostrar_componente':
        final coords = result['coordinates'];
        final label = result['component'] as String? ?? result['componente'] as String? ?? 'Componente';
        if (coords != null && coords is List && coords.length == 4) {
          final doubles = coords.map<double>((x) => (x as num).toDouble()).toList();
          onBoundingBox?.call(doubles, label);
        }
        break;

      case 'generar_guia_visual_ensamblaje':
        final imgB64 = result['image_b64'] as String? ?? result['image'] as String?;
        final imgUrl = result['image_url'] as String?;
        final ctx = result['context'] as String? ?? 'Esquema de Ensamblaje';
        Uint8List? imgBytes;
        if (imgB64 != null) {
          try { imgBytes = base64Decode(imgB64); } catch (_) {}
        }
        onVisualGuide?.call(imgBytes, imgUrl, ctx);
        break;

      case 'safety_guardian_agent':
        final riesgos = result['riesgos'] as String?;
        if (riesgos != null && riesgos.isNotEmpty) {
          onSafetyAlert?.call(riesgos);
        }
        break;

      case 'consultar_logistica_repuestos':
        final rawLinks = result['parts_links'];
        if (rawLinks != null && rawLinks is List && rawLinks.isNotEmpty) {
          final links = rawLinks.map<String>((e) => e.toString()).toList();
          debugPrint('🛒 PARTS LINKS recibidos: $links');
          onPartsLinks?.call(links);
        }
        break;
    }
  }

  // =====================================================================
  // Sending data to Gemini Live via raw WebSocket
  // =====================================================================

  /// Send microphone audio (PCM 16kHz mono) directly to Gemini
  void sendAudio(Uint8List pcmData) {
    if (_wsChannel == null || !_isConnected) return;
    try {
      final message = {
        'realtimeInput': {
          'mediaChunks': [{
            'mimeType': 'audio/pcm;rate=16000',
            'data': base64Encode(pcmData),
          }]
        }
      };
      _wsChannel!.sink.add(jsonEncode(message));
    } catch (e) {
      debugPrint('Error sending audio to Gemini: $e');
    }
  }

  /// Send camera frame (JPEG) directly to Gemini
  void sendImage(Uint8List jpegData) {
    if (_wsChannel == null || !_isConnected) return;
    try {
      final message = {
        'realtimeInput': {
          'mediaChunks': [{
            'mimeType': 'image/jpeg',
            'data': base64Encode(jpegData),
          }]
        }
      };
      _wsChannel!.sink.add(jsonEncode(message));
    } catch (e) {
      debugPrint('Error sending image to Gemini: $e');
    }
  }

  /// Signal end of turn (user stopped speaking)
  void sendEndOfTurn() {
    if (_wsChannel == null || !_isConnected) return;
    try {
      final message = {
        'clientContent': {
          'turns': [{'role': 'user', 'parts': [{'text': ' '}]}],
          'turnComplete': true,
        }
      };
      _wsChannel!.sink.add(jsonEncode(message));
    } catch (e) {
      debugPrint('Error sending end of turn: $e');
    }
  }

  /// Disconnect from Gemini Live
  void disconnect() {
    _isConnected = false;
    _wsChannel?.sink.close();
    _wsChannel = null;
    onLog('🔌 Gemini Direct disconnected');
  }
}

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:record/record.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'gemini_direct_service.dart';

Uint8List _addWavHeader(Uint8List pcmData) {
  int channels = 1;
  int sampleRate = 24000;
  int bitRate = 16;
  int byteRate = sampleRate * channels * (bitRate ~/ 8);
  int dataSize = pcmData.length;

  var header = ByteData(44);
  header.setUint8(0, 0x52); // 'R'
  header.setUint8(1, 0x49); // 'I'
  header.setUint8(2, 0x46); // 'F'
  header.setUint8(3, 0x46); // 'F'
  header.setUint32(4, 36 + dataSize, Endian.little);
  header.setUint8(8, 0x57); // 'W'
  header.setUint8(9, 0x41); // 'A'
  header.setUint8(10, 0x56); // 'V'
  header.setUint8(11, 0x45); // 'E'
  header.setUint8(12, 0x66); // 'f'
  header.setUint8(13, 0x6D); // 'm'
  header.setUint8(14, 0x74); // 't'
  header.setUint8(15, 0x20); // ' '
  header.setUint32(16, 16, Endian.little); // Format chunk size
  header.setUint16(20, 1, Endian.little); // Audio format (1 = PCM)
  header.setUint16(22, channels, Endian.little);
  header.setUint32(24, sampleRate, Endian.little);
  header.setUint32(28, byteRate, Endian.little);
  header.setUint16(32, channels * (bitRate ~/ 8), Endian.little);
  header.setUint16(34, bitRate, Endian.little);
  header.setUint8(36, 0x64); // 'd'
  header.setUint8(37, 0x61); // 'a'
  header.setUint8(38, 0x74); // 't'
  header.setUint8(39, 0x61); // 'a'
  header.setUint32(40, dataSize, Endian.little);

  var wavData = Uint8List(44 + dataSize);
  wavData.setAll(0, header.buffer.asUint8List());
  wavData.setAll(44, pcmData);
  return wavData;
}

List<CameraDescription> cameras = [];

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    cameras = await availableCameras();
  } on CameraException catch (e) {
    debugPrint('Error in fetching the cameras: $e');
  }
  runApp(const AgnosticApp());
}

class AgnosticApp extends StatelessWidget {
  const AgnosticApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Agnostic Assistant',
      theme: ThemeData(
        brightness: Brightness.dark, // Better for field work
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      home: const CameraScreen(),
    );
  }
}

class CameraScreen extends StatefulWidget {
  const CameraScreen({Key? key}) : super(key: key);

  @override
  _CameraScreenState createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  CameraController? _controller;
  bool _isCameraInitialized = false;
  bool _isRecordingAudio = false;
  
  // 🔀 HYBRID MODE FLAG — Set to false to revert to original Python relay
  static const bool _useDirectGemini = false;

  // App State
  String _selectedMode = 'hogar'; // 'residential' or 'hogar'
  String _currentLocation = "Desconocida";
  List<String> _consoleLogs = ["System Initialized."];
  bool _isConsoleExpanded = false;
  
  // Visual Guide Overlay (sent by Gemini when ambiguity is detected)
  String? _visualGuideImageUrl;   // fallback: URL
  Uint8List? _visualGuideImageBytes; // preferred: base64 bytes from Imagen 3

  // Safety Alert Banner (injected by the Guardián parallel agent)
  String? _safetyAlertMessage;
  Timer? _safetyAlertTimer;  // Auto-dismiss after 8 seconds

  // Bounding Box Overlay (Proactive Vision Agent)
  List<double>? _boundingBox;
  String? _boundingBoxLabel;
  Timer? _boundingBoxTimer; // Auto-dismiss after 5 seconds

  // 🛒 Parts Links Overlay (MercadoLibre links from logistics agent)
  List<String> _partsLinks = [];
  Timer? _partsLinksTimer; // Auto-dismiss after 30 seconds

  // 📊 Judge Mode Telemetry
  bool _isJudgeModeActive = false;
  final List<Map<String, dynamic>> _telemetryEvents = [];

  // WebSocket for Gemini Live API (original relay mode)
  WebSocketChannel? _channel;

  // 🔀 Direct Gemini service (hybrid mode)
  GeminiDirectService? _geminiService;

  // Audio Processing
  final AudioRecorder _audioRecorder = AudioRecorder();
  final AudioPlayer _audioPlayer = AudioPlayer();
  StreamSubscription<Uint8List>? _micStreamSub;
  
  // Audio Playback Queue
  bool _isPlaying = false;
  final List<Uint8List> _audioQueue = [];
  Timer? _cameraFrameTimer;
  Timer? _backgroundFrameTimer; // Captures frames for parallel agents (NO mic/WS needed)
  Uint8List? _latestFrame;  // Stores the latest camera frame for safety checks

  // User ID for ConnectionManager cross-injection (can be made dynamic per user)
  final String _userId = 'default';

  // Backend base URL
  static const String _backendUrl = 'https://agnostic-backend-532234202617.us-central1.run.app';

  void _enqueueAudio(Uint8List pcmData) {
    _audioQueue.add(pcmData);
    // If not currently playing, try to trigger playback.
    // _playNextInQueue will check if the pre-buffer condition is met.
    if (!_isPlaying) {
      _playNextInQueue();
    }
  }

  /// Clears all pending audio and stops current playback (for barge-in)
  void _clearAudioQueue() {
    _audioQueue.clear();
    _isPlaying = false;
    _audioPlayer.stop();
  }

  Future<void> _playNextInQueue() async {
    if (_audioQueue.isEmpty) {
      _isPlaying = false;
      return;
    }

    // --- PRE-BUFFERING LOGIC (Option 1) ---
    // Wait until we have at least 3 chunks (~24KB total, ~750ms) before starting playback.
    // This merges small streaming chunks into one solid continuous WAV file,
    // eliminating the stuttering/micro-pauses caused by the audio player.
    if (!_isPlaying && _audioQueue.length < 3) {
      // Not enough chunks to ensure smooth playback yet.
      // Wait for more chunks to arrive via _enqueueAudio.
      return; 
    }

    _isPlaying = true;
    
    // Drain up to 6 chunks at a time into one buffer for smooth continuous playback.
    // This allows catching up if the queue gets too large, while keeping chunks big.
    final buffer = BytesBuilder();
    final count = _audioQueue.length < 6 ? _audioQueue.length : 6;
    for (int i = 0; i < count; i++) {
      buffer.add(_audioQueue.removeAt(0));
    }

    try {
      final wavData = _addWavHeader(buffer.toBytes());
      await _audioPlayer.play(BytesSource(wavData));
    } catch (e) {
      debugPrint("Error playing audio: $e");
      _isPlaying = false;
      _playNextInQueue(); // Try next chunk
    }
  }

  @override
  void initState() {
    super.initState();
    _requestPermissionsAndInitCamera();
    
    _audioPlayer.onPlayerStateChanged.listen((state) {
        if (state == PlayerState.completed) {
            _isPlaying = false;
            _playNextInQueue(); // Play next buffered chunk
        }
    });

  }



  Future<void> _requestPermissionsAndInitCamera() async {
    _addLog("Requesting permissions...");
    
    // Request all permissions at once for a single, clean dialog flow on Android
    Map<Permission, PermissionStatus> statuses = await [
      Permission.camera,
      Permission.microphone,
      Permission.locationWhenInUse, // This is the key missing one!
    ].request();

    _addLog("Perms: Cam:${statuses[Permission.camera]}, Mic:${statuses[Permission.microphone]}, GPS:${statuses[Permission.locationWhenInUse]}");

    // locationWhenInUse not in the map for older geolocator... sync via Geolocator too
    LocationPermission geoPermission = await Geolocator.checkPermission();
    if (geoPermission == LocationPermission.denied) {
        geoPermission = await Geolocator.requestPermission();
    }
    if (geoPermission == LocationPermission.deniedForever) {
       _addLog("GPS PERM DENIED FOREVER. Please open settings.");
       await openAppSettings();
    }

    if (statuses[Permission.camera]!.isGranted && statuses[Permission.microphone]!.isGranted) {
      // Fetch GPS if available
      final gpsGranted = statuses[Permission.locationWhenInUse]?.isGranted == true ||
                         geoPermission == LocationPermission.always ||
                         geoPermission == LocationPermission.whileInUse;
      if (gpsGranted) {
        _addLog("GPS Permission Granted. Fetching coordinates...");
        try {
          Position? position = await Geolocator.getLastKnownPosition();
          if (position == null) {
            _addLog("Last known GPS null. Getting current...");
            position = await Geolocator.getCurrentPosition(
              desiredAccuracy: LocationAccuracy.high,
              timeLimit: const Duration(seconds: 10),
            );
          }
          _currentLocation = "${position.latitude},${position.longitude}";
          _addLog("GPS FIXED: $_currentLocation");
        } catch (e) {
            _addLog("GPS Fetch Failed: $e. Using default location.");
        }
      } else {
        _addLog("GPS Permission NOT granted by user.");
      }

      if (cameras.isNotEmpty) {
        _controller = CameraController(
          cameras[0], // Back camera usually
          ResolutionPreset.high,
          enableAudio: false, // We will handle audio separately for Gemini
        );

        try {
          await _controller!.initialize();
          setState(() {
            _isCameraInitialized = true;
          });
          _addLog("Camera initialized successfully.");
          // 🚀 Start ALL parallel agent timers IMMEDIATELY after camera init
          // This happens BEFORE WebSocket, BEFORE mic — zero latency from the start
          _startBackgroundFrameCapturer();
          _connectWebSocket();
        } catch (e) {
          debugPrint("Error initializing camera: $e");
          _addLog("Error: Camera failed to init.");
        }
      } else {
        _addLog("Error: No cameras available.");
      }
    } else {
      _addLog("Permissions not granted.");
    }
  }

  void _addLog(String msg) {
    debugPrint("LOG: $msg");
    setState(() {
      _consoleLogs.insert(0, "[${DateTime.now().toLocal().toString().split(' ')[1].substring(0,8)}] $msg");
      // Keep only last 50 logs to avoid memory issues
      if (_consoleLogs.length > 50) _consoleLogs.removeLast();
    });
  }

  void _connectWebSocket() async {
    _addLog("Connecting with Location: $_currentLocation...");

    // 🔀 HYBRID MODE: Connect directly to Gemini Live
    if (_useDirectGemini) {
      _addLog("🔀 Hybrid mode: Direct Gemini connection...");
      try {
        _geminiService = GeminiDirectService(
          backendUrl: _backendUrl,
          onAudioReceived: (bytes) => _enqueueAudio(bytes),
          onToolExecuted: (result, name) {
            _addLog("Tool: $name");
          },
          onLog: (msg) => _addLog(msg),
          onInterrupted: () {
            _addLog("🔇 BARGE-IN: Cortando audio de Gemini...");
            _clearAudioQueue();
          },
          onBoundingBox: (coords, label) {
            _addLog("🎯 Caja Delimitadora: $label $coords");
            setState(() {
              _boundingBox = coords;
              _boundingBoxLabel = label;
            });
            _boundingBoxTimer?.cancel();
            _boundingBoxTimer = Timer(const Duration(seconds: 5), () {
              if (mounted) setState(() {
                _boundingBox = null;
                _boundingBoxLabel = null;
              });
            });
          },
          onVisualGuide: (imgBytes, imgUrl, ctx) {
            _addLog("📸 Guía Visual: $ctx");
            setState(() {
              _visualGuideImageBytes = imgBytes;
              _visualGuideImageUrl = imgUrl;
            });
          },
          onFlashlight: (on) => _setFlashlight(on),
          onSafetyAlert: (msg) {
            _addLog("🚨 ALERTA DE SEGURIDAD: $msg");
            setState(() => _safetyAlertMessage = msg);
            _safetyAlertTimer?.cancel();
            _safetyAlertTimer = Timer(const Duration(seconds: 8), () {
              if (mounted) setState(() => _safetyAlertMessage = null);
            });
          },
          onPartsLinks: (links) {
            _addLog("🛒 Links ML: ${links.length} resultados");
            setState(() => _partsLinks = links);
            _partsLinksTimer?.cancel();
            _partsLinksTimer = Timer(const Duration(seconds: 30), () {
              if (mounted) setState(() => _partsLinks = []);
            });
          },
          frameProvider: () => _latestFrame,
        );

        await _geminiService!.connect(
          mode: _selectedMode,
          location: _currentLocation,
          userId: _userId,
        );

        // Auto-start microphone
        if (!_isRecordingAudio) {
          _toggleMic();
        }
      } catch (e) {
        _addLog("❌ Hybrid connection failed: $e");
        _addLog("⚠️ Check if gemini_live package is compatible.");
      }
      return;
    }

    // =====================================================================
    // ORIGINAL MODE: WebSocket relay through Python (unchanged)
    // =====================================================================
    final encodedLocation = Uri.encodeComponent(_currentLocation);
    String wsUrlStr = 'wss://agnostic-backend-532234202617.us-central1.run.app/ws/gemini-live?mode=$_selectedMode&location=$encodedLocation&user_id=$_userId';
    
    // Simulate receiving an emergency work order from an external system if in Industrial mode
    // Added a persistent static session_id so that if connection drops, it re-joins the same session context.
    if (_selectedMode == 'industrial') {
        const testMachine = "Bomba 5";
        const testIssue = "Mantenimiento preventivo: Cambio de turbina";
        const sessionId = "WO-9911-BOMBA5"; // Simulated static session ID
        wsUrlStr += '&emergency_machine=${Uri.encodeComponent(testMachine)}&emergency_issue=${Uri.encodeComponent(testIssue)}&session_id=${Uri.encodeComponent(sessionId)}';
        _addLog("Simulando push de Orden Preventiva: $testMachine");
        _addLog("Session ID Fijo: $sessionId");
    }

    final wsUrl = Uri.parse(wsUrlStr);
    
    try {
      _channel = WebSocketChannel.connect(wsUrl);
      _addLog("Connected to Backend ($_selectedMode mode)");
      
      _channel!.stream.listen((message) async {
         // Receive data from backend (Tools or Audio)
         if (message is String) {
             try {
                 final decoded = jsonDecode(message);
                 if (decoded['type'] == 'tool_call') {
                     _addLog("Tool: ${decoded['name']}");
                 } else if (decoded['type'] == 'visual_guide_push' || decoded['type'] == 'visual_guide_image') {
                     final imgB64 = decoded['image_b64'] ?? decoded['image'] as String?;
                     final imgUrl = decoded['image_url'] as String?;
                     final ctx = decoded['context'] as String? ?? 'Esquema de Ensamblaje';
                     _addLog("📸 Guía Visual (Nano Banana 2): $ctx");
                     setState(() {
                         _visualGuideImageBytes = imgB64 != null ? base64Decode(imgB64) : null;
                         _visualGuideImageUrl = imgUrl;
                     });
                 } else if (decoded['type'] == 'safety_alert') {
                     // 🚨 Safety alert from the Guardián parallel agent
                     final msg = decoded['message'] as String? ?? 'PELIGRO DETECTADO';
                     _addLog("🚨 ALERTA DE SEGURIDAD: $msg");
                     setState(() => _safetyAlertMessage = msg);
                     // Auto-dismiss banner after 8 seconds
                     _safetyAlertTimer?.cancel();
                     _safetyAlertTimer = Timer(const Duration(seconds: 8), () {
                         if (mounted) setState(() => _safetyAlertMessage = null);
                     });
                 } else if (decoded['type'] == 'bounding_box') {
                     // 🎯 Proactive Bounding Box from Eagle Eye
                     final coordsList = decoded['coordinates'] as List<dynamic>?;
                     if (coordsList != null && coordsList.length == 4) {
                         final coords = coordsList.map((x) => (x as num).toDouble()).toList();
                         final label = decoded['component'] as String? ?? 'Componente';
                         _addLog("🎯 Caja Delimitadora: $label $coords");
                         setState(() {
                             _boundingBox = coords; // [ymin, xmin, ymax, xmax] normalizadas 0-1000
                             _boundingBoxLabel = label;
                         });
                         _boundingBoxTimer?.cancel();
                         _boundingBoxTimer = Timer(const Duration(seconds: 5), () {
                             if (mounted) setState(() {
                                 _boundingBox = null;
                                 _boundingBoxLabel = null;
                             });
                         });
                     }
                  } else if (decoded['type'] == 'interrupted') {
                      // 🔇 Barge-In: User spoke over Gemini, stop playback immediately
                      _addLog("🔇 BARGE-IN: Cortando audio de Gemini...");
                      _clearAudioQueue();
                  } else if (decoded['type'] == 'telemetry') {
                      // 📊 Judge Mode telemetry event
                      if (_isJudgeModeActive) {
                        setState(() {
                          _telemetryEvents.insert(0, decoded);
                          if (_telemetryEvents.length > 20) _telemetryEvents.removeLast();
                        });
                      }
                  } else if (decoded['type'] == 'flashlight') {
                      // 🔦 Flashlight control from Gemini Agent
                      final action = decoded['action'] as String? ?? 'off';
                      final on = action.toLowerCase() == 'on';
                      _setFlashlight(on);
                      _addLog("🔦 Recibido comando linterna: ${on ? 'ON' : 'OFF'}");
                  } else if (decoded['type'] == 'parts_links') {

                       // MercadoLibre links from logistics agent

                       final rawLinks = decoded['links'] as List<dynamic>?;

                       if (rawLinks != null && rawLinks.isNotEmpty) {

                           final links = rawLinks.map<String>((e) => e.toString()).toList();

                           _addLog('Links ML: ' + links.length.toString() + ' resultados');

                           setState(() => _partsLinks = links);

                           _partsLinksTimer?.cancel();

                           _partsLinksTimer = Timer(const Duration(seconds: 30), () {

                               if (mounted) setState(() => _partsLinks = []);

                           });

                       }

                  }

             } catch(e) {
                 debugPrint("Received non-json string from WS");
             }
         } else {
             try {
                final bytes = message as Uint8List;
                _enqueueAudio(bytes);
             } catch(e) {
                debugPrint("Error receiving audio: $e");
             }
         }
      },
      onError: (error) {
          _addLog("WS Error: $error");
      },
      onDone: () {
          _addLog("WS Disconnected.");
          if (_isRecordingAudio && !_isChangingMode) {
             _toggleMic(); // Auto-stop mic if disconnected (unless changing mode)
          }
      });
      
      // 🛡️ Start the Guardián safety frame timer INDEPENDENTLY
      // Already started from camera init. Skip duplicate start.
      // Auto-start microphone for true Hands-Free VAD
      if (!_isRecordingAudio) {
         _toggleMic();
      }
      
    } catch (e) {
      _addLog("WebSocket Connection Error: $e");
    }
  }

  bool _isCapturingFrame = false;

  /// 📷 Captures frames every 2s for parallel agents (INDEPENDENT of mic/WS)
  void _startBackgroundFrameCapturer() {
    _backgroundFrameTimer?.cancel();
    _backgroundFrameTimer = Timer.periodic(const Duration(seconds: 2), (timer) async {
      if (!_isCameraInitialized || _controller == null || _isCapturingFrame) return;
      
      _isCapturingFrame = true;
      try {
        final XFile picture = await _controller!.takePicture();
        _latestFrame = await picture.readAsBytes();
      } catch (e) {
        _addLog("Error capturing frame: $e");
      } finally {
        _isCapturingFrame = false;
      }
    });
    _addLog("📷 Background frame capturer started (for WebSocket streaming).");

    // NOTA: Los timers HTTP de Vision y Safety fueron removidos.
    // Ahora TODO el análisis se realiza inyectando el _latestFrame 
    // a través del WebSocket de Gemini Live.
  }

  void _setFlashlight(bool on) async {
    if (_controller != null && _controller!.value.isInitialized) {
      if (_isCapturingFrame) {
        // Wait a tiny bit for the current frame capture to release the hardware lock
        await Future.delayed(const Duration(milliseconds: 300));
      }
      try {
        await _controller!.setFlashMode(on ? FlashMode.torch : FlashMode.off);
        _addLog("flashlight LED ${on ? 'ON' : 'OFF'}");
      } catch (e) {
        _addLog("Error setting flashlight: $e");
      }
    }
  }

  bool _isChangingMode = false;

  void _switchMode(String mode) async {
    setState(() {
      _selectedMode = mode;
    });
    _addLog("Switched to $mode mode. Reconnecting...");
    
    // Activar escudo protector para ignorar el onDone engañoso
    _isChangingMode = true;
    if (_useDirectGemini) {
      _geminiService?.disconnect();
    } else {
      _channel?.sink.close();
    }
    
    // Esperar a que el sistema cierre y se asiente
    await Future.delayed(const Duration(milliseconds: 300));
    _isChangingMode = false;
    
    _connectWebSocket();
  }

  void _toggleMic() async {
    setState(() {
      _isRecordingAudio = !_isRecordingAudio;
    });
    
    if (_isRecordingAudio) {
        _addLog("Mic Opened - Listening...");
        if (await _audioRecorder.hasPermission()) {
          final stream = await _audioRecorder.startStream(const RecordConfig(
            encoder: AudioEncoder.pcm16bits,
            sampleRate: 16000,
            numChannels: 1,
            echoCancel: true,
            noiseSuppress: true,
            autoGain: true,
          ));
          _micStreamSub = stream.listen((data) {
            if (_useDirectGemini && _geminiService != null) {
              // 🔀 HYBRID: Send audio directly to Gemini (no Python relay)
              _geminiService!.sendAudio(Uint8List.fromList(data));
            } else if (_channel != null) {
              // ORIGINAL: Send audio to Python backend
              final payload = jsonEncode({
                  "type": "audio",
                  "data": base64Encode(data)
              });
              _channel!.sink.add(payload);
            }
          });
        }
        
        // Start streaming video frames (1 FPS)
        _cameraFrameTimer = Timer.periodic(const Duration(seconds: 1), (timer) async {
           if (_isCameraInitialized && _controller != null && !_isCapturingFrame) {
               _isCapturingFrame = true;
               try {
                   final XFile picture = await _controller!.takePicture();
                   final bytes = await picture.readAsBytes();
                   // Cache the frame for the safety frame timer and Snapshot-on-Demand
                   _latestFrame = bytes;

                   if (_useDirectGemini && _geminiService != null) {
                     // 🔀 HYBRID: Send frame directly to Gemini
                     _geminiService!.sendImage(bytes);
                   } else if (_channel != null) {
                     // ORIGINAL: Send frame to Python backend
                     final payload = jsonEncode({
                        "type": "image",
                        "data": base64Encode(bytes)
                     });
                     _channel!.sink.add(payload);
                   }
               } catch (e) {
                   debugPrint("Error capturing frame: $e");
               } finally {
                   _isCapturingFrame = false;
               }
           }
        });
        
    } else {
        _addLog("Mic Closed (Vision Paused).");
        await _micStreamSub?.cancel();
        await _audioRecorder.stop();
        _cameraFrameTimer?.cancel();
        
        // Notify that user finished talking (forces Gemini to reply)
        if (_useDirectGemini && _geminiService != null) {
          _geminiService!.sendEndOfTurn();
          _addLog("Sent End-of-Turn signal (direct).");
        } else if (_channel != null) {
           final payload = jsonEncode({"type": "end_turn"});
           _channel!.sink.add(payload);
           _addLog("Sent End-of-Turn signal.");
        }
    }
  }

  @override
  void dispose() {
    _backgroundFrameTimer?.cancel();
    _cameraFrameTimer?.cancel();
    _safetyAlertTimer?.cancel();
    _boundingBoxTimer?.cancel();
    _controller?.dispose();
    _geminiService?.disconnect();
    _channel?.sink.close();
    _micStreamSub?.cancel();
    _audioRecorder.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  // --- UI COMPONENTS --- //

  Widget _buildCameraPreview() {
    if (_isCameraInitialized && _controller != null) {
      return SizedBox.expand(
        child: FittedBox(
          fit: BoxFit.cover,
          child: SizedBox(
             width: _controller!.value.previewSize?.height ?? 1,
             height: _controller!.value.previewSize?.width ?? 1,
             child: Stack(
               fit: StackFit.expand,
               children: [
                 CameraPreview(_controller!),
                 if (_boundingBox != null)
                   IgnorePointer(
                     child: CustomPaint(
                       painter: BoundingBoxPainter(
                         boundingBox: _boundingBox!,
                         label: _boundingBoxLabel ?? '🎯 Objetivo',
                       ),
                     ),
                   ),
               ],
             ),
          )
        ),
      );
    } else {
      return const Center(child: CircularProgressIndicator());
    }
  }

  Widget _buildModeSelector() {
    return Positioned(
      top: 50,
      left: 16,
      right: 16,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.black54,
          borderRadius: BorderRadius.circular(30),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            TextButton(
              onPressed: () => _switchMode('residential'),
              style: TextButton.styleFrom(
                backgroundColor: _selectedMode == 'residential' ? Colors.green : Colors.transparent,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              ),
              child: const Text("🏠 Residencial", style: TextStyle(color: Colors.white, fontSize: 13)),
            ),
            TextButton(
              onPressed: () => _switchMode('hogar'),
              style: TextButton.styleFrom(
                backgroundColor: _selectedMode == 'hogar' ? Colors.deepPurple : Colors.transparent,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              ),
              child: const Text("🔧 Hogar", style: TextStyle(color: Colors.white, fontSize: 13)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGiantMicButton() {
    return Positioned(
      bottom: 120,
      left: 0,
      right: 0,
      child: Center(
        child: Column(
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              height: _isRecordingAudio ? 120 : 100,
              width: _isRecordingAudio ? 120 : 100,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _isRecordingAudio ? Colors.redAccent : Colors.white24,
                border: Border.all(
                  color: _isRecordingAudio ? Colors.red : Colors.white, 
                  width: 4
                ),
                boxShadow: [
                  if (_isRecordingAudio)
                     BoxShadow(color: Colors.red.withOpacity(0.6), blurRadius: 20, spreadRadius: 5)
                ]
              ),
              child: Icon(
                _isRecordingAudio ? Icons.mic : Icons.mic_none,
                size: 50,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 10),
            if (_isRecordingAudio)
              const Text("Escuchando...", style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold, fontSize: 16))
            else
              const Text("Esperando conexión...", style: TextStyle(color: Colors.white54, fontSize: 14)),
          ],
        ),
      ),
    );
  }

  Widget _buildCollapsibleConsole() {
    return Positioned(
      bottom: 0,
      left: 0,
      right: 0,
      child: GestureDetector(
        onVerticalDragUpdate: (details) {
          if (details.delta.dy < -10) {
             setState(() => _isConsoleExpanded = true);
          } else if (details.delta.dy > 10) {
             setState(() => _isConsoleExpanded = false);
          }
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          height: _isConsoleExpanded ? 300 : 80,
          decoration: const BoxDecoration(
            color: Colors.black87,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              // Drag Handle
              Container(
                margin: const EdgeInsets.only(top: 10, bottom: 5),
                height: 5,
                width: 50,
                decoration: BoxDecoration(
                  color: Colors.grey,
                  borderRadius: BorderRadius.circular(5),
                ),
              ),
              // Latest Log Summary (when collapsed)
              if (!_isConsoleExpanded)
                 Padding(
                   padding: const EdgeInsets.symmetric(horizontal: 20),
                   child: Text(
                     _consoleLogs.isNotEmpty ? _consoleLogs.first : "...",
                     style: const TextStyle(color: Colors.greenAccent, fontSize: 14),
                     maxLines: 1,
                     overflow: TextOverflow.ellipsis,
                   ),
                 ),
              // Full Logs (when expanded)
              if (_isConsoleExpanded)
                 Expanded(
                   child: ListView.builder(
                     padding: const EdgeInsets.all(16),
                     itemCount: _consoleLogs.length,
                     itemBuilder: (context, index) {
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8.0),
                          child: Text(
                            _consoleLogs[index],
                            style: const TextStyle(color: Colors.greenAccent, fontFamily: 'monospace', fontSize: 12),
                          ),
                        );
                     }
                   ),
                 )
            ],
          ),
        ),
      ),
    );
  }

  // 🛒 Parts Links Overlay: shown when logistics agent finds ML links
  Widget _buildPartsLinksOverlay() {
    if (_partsLinks.isEmpty) return const SizedBox.shrink();
    return Positioned(
      bottom: 100,
      left: 12,
      right: 12,
      child: GestureDetector(
        onTap: () {},
        child: Container(
          decoration: BoxDecoration(
            color: Colors.black87,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.amberAccent.withOpacity(0.6), width: 1),
          ),
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Text('🛒 ', style: TextStyle(fontSize: 16)),
                  const Expanded(
                    child: Text(
                      'Repuestos en MercadoLibre',
                      style: TextStyle(color: Colors.amberAccent, fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                  ),
                  GestureDetector(
                    onTap: () { _partsLinksTimer?.cancel(); setState(() => _partsLinks = []); },
                    child: const Icon(Icons.close, color: Colors.white54, size: 18),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ..._partsLinks.asMap().entries.map((entry) {
                final idx = entry.key + 1;
                final url = entry.value;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: GestureDetector(
                    onTap: () async {
                      // Open URL in browser
                      try {
                        final http.Response _ = await http.get(Uri.parse(url));
                      } catch (_) {}
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      decoration: BoxDecoration(
                        color: Colors.amber.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.amber.withOpacity(0.3)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.open_in_browser, color: Colors.amberAccent, size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Resultado $idx: Ver en MercadoLibre',
                              style: const TextStyle(color: Colors.white, fontSize: 12),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }).toList(),
              const Text('Toca para abrir', style: TextStyle(color: Colors.white38, fontSize: 10)),
            ],
          ),
        ),
      ),
    );
  }

  // 🚨 Red banner shown when the Guardián parallel agent detects a safety hazard
  Widget _buildSafetyAlertBanner() {
    if (_safetyAlertMessage == null) return const SizedBox.shrink();
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: GestureDetector(
        onTap: () {
          _safetyAlertTimer?.cancel();
          setState(() => _safetyAlertMessage = null);
        },
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 48, 16, 16),
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xFFB71C1C), Color(0xFFD32F2F)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('🚨 ', style: TextStyle(fontSize: 22)),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'ALERTA DE SEGURIDAD',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14, letterSpacing: 1.2),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _safetyAlertMessage!,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Toca para cerrar',
                      style: TextStyle(color: Colors.white60, fontSize: 11),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // Overlay shown when Gemini sends a visual guide image push
  Widget _buildVisualGuideOverlay() {
    final hasImage = _visualGuideImageBytes != null || _visualGuideImageUrl != null;
    if (!hasImage) return const SizedBox.shrink();
    return Positioned.fill(
      child: GestureDetector(
        onTap: () => setState(() {
          _visualGuideImageUrl = null;
          _visualGuideImageBytes = null;
        }),
        child: Container(
          color: Colors.black87,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Padding(
                padding: EdgeInsets.only(bottom: 12),
                child: Text(
                  "📸 Guía Visual de Gemini",
                  style: TextStyle(color: Colors.cyanAccent, fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  // Prefer Imagen 3 bytes (Image.memory), fallback to URL (Image.network)
                  child: _visualGuideImageBytes != null
                      ? Image.memory(
                          _visualGuideImageBytes!,
                          fit: BoxFit.contain,
                          errorBuilder: (ctx, err, st) => const Center(
                            child: Text('No se pudo mostrar la imagen', style: TextStyle(color: Colors.redAccent)),
                          ),
                        )
                      : Image.network(
                          _visualGuideImageUrl!,
                          fit: BoxFit.contain,
                          loadingBuilder: (ctx, child, progress) {
                            if (progress == null) return child;
                            return const Center(child: CircularProgressIndicator(color: Colors.cyanAccent));
                          },
                          errorBuilder: (ctx, err, st) => const Center(
                            child: Text('No se pudo cargar la imagen', style: TextStyle(color: Colors.redAccent)),
                          ),
                        ),
                ),
              ),
              const Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  "Toca para cerrar",
                  style: TextStyle(color: Colors.white54, fontSize: 13),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }



  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // 1. Camera Native View Fullscreen (Now includes Bounding Box)
          _buildCameraPreview(),

          // 2. Translucent Overlay for UI contrast
          Container(color: Colors.black.withOpacity(0.2)),

          // 3. Mode Selector (Industrial / Residencial / Hogar)
          _buildModeSelector(),

          // 4. Giant Floating MicButton
          _buildGiantMicButton(),

          // 5. Collapsible Console
          _buildCollapsibleConsole(),

          // 6. Visual Guide Overlay (shown when Gemini sends an image push)
          _buildVisualGuideOverlay(),

          // 6b. Parts Links Overlay (MercadoLibre links from logistics agent)
          _buildPartsLinksOverlay(),

          // 7. Safety Alert Banner (topmost layer, from Guardián parallel agent)
          _buildSafetyAlertBanner(),

          // 8. Judge Mode Telemetry Overlay
          if (_isJudgeModeActive) _buildJudgeModeOverlay(),

          // 9. Judge Mode Toggle Button
          _buildJudgeModeToggle(),
        ],
      ),
    );
  }

  // 📊 JUDGE MODE: Toggle button (bottom-right)
  Widget _buildJudgeModeToggle() {
    return Positioned(
      bottom: 90,
      right: 16,
      child: GestureDetector(
        onTap: () => setState(() {
          _isJudgeModeActive = !_isJudgeModeActive;
          if (!_isJudgeModeActive) _telemetryEvents.clear();
        }),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: _isJudgeModeActive
                ? Colors.cyanAccent.withOpacity(0.3)
                : Colors.black45,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: _isJudgeModeActive ? Colors.cyanAccent : Colors.white30,
              width: 1.5,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.analytics_outlined,
                color: _isJudgeModeActive ? Colors.cyanAccent : Colors.white54,
                size: 18,
              ),
              const SizedBox(width: 4),
              Text(
                'JUDGE',
                style: TextStyle(
                  color: _isJudgeModeActive ? Colors.cyanAccent : Colors.white54,
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // 📊 JUDGE MODE: Telemetry overlay panel
  Widget _buildJudgeModeOverlay() {
    return Positioned(
      top: 100,
      right: 8,
      child: Container(
        width: 220,
        constraints: const BoxConstraints(maxHeight: 400),
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.75),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.cyanAccent.withOpacity(0.4), width: 1),
          boxShadow: [
            BoxShadow(
              color: Colors.cyanAccent.withOpacity(0.1),
              blurRadius: 20,
              spreadRadius: 2,
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.cyanAccent.withOpacity(0.2),
                    Colors.transparent,
                  ],
                ),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(15)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 8, height: 8,
                    decoration: BoxDecoration(
                      color: Colors.greenAccent,
                      shape: BoxShape.circle,
                      boxShadow: [BoxShadow(color: Colors.greenAccent.withOpacity(0.5), blurRadius: 6)],
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    'AGENT TELEMETRY',
                    style: TextStyle(
                      color: Colors.cyanAccent,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1.5,
                    ),
                  ),
                ],
              ),
            ),
            // Events List
            if (_telemetryEvents.isEmpty)
              const Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  'Waiting for agent activity...',
                  style: TextStyle(color: Colors.white38, fontSize: 11, fontStyle: FontStyle.italic),
                ),
              )
            else
              ...(_telemetryEvents.take(10).map((evt) {
                final isRunning = evt['status'] == 'running';
                final isDone = evt['status'] == 'done';
                final isError = evt['status'] == 'error';
                final agent = evt['agent'] as String? ?? 'Unknown';
                final detail = evt['detail'] as String? ?? '';
                final durationMs = evt['duration_ms'] as int? ?? 0;

                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Status indicator
                      Container(
                        margin: const EdgeInsets.only(top: 3),
                        width: 8, height: 8,
                        decoration: BoxDecoration(
                          color: isRunning
                              ? Colors.orangeAccent
                              : isDone
                                  ? Colors.greenAccent
                                  : Colors.redAccent,
                          shape: BoxShape.circle,
                          boxShadow: isRunning
                              ? [BoxShadow(color: Colors.orangeAccent.withOpacity(0.6), blurRadius: 6)]
                              : null,
                        ),
                      ),
                      const SizedBox(width: 6),
                      // Agent name + detail
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              agent,
                              style: TextStyle(
                                color: isRunning ? Colors.orangeAccent : Colors.white70,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            if (isDone && durationMs > 0)
                              Text(
                                '✓ ${(durationMs / 1000).toStringAsFixed(1)}s',
                                style: const TextStyle(color: Colors.greenAccent, fontSize: 10),
                              ),
                            if (isError)
                              Text(
                                '✗ Error',
                                style: const TextStyle(color: Colors.redAccent, fontSize: 10),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }).toList()),
            const SizedBox(height: 6),
          ],
        ),
      ),
    );
  }
}

class BoundingBoxPainter extends CustomPainter {
  final List<double> boundingBox; // [ymin, xmin, ymax, xmax] normalized 0-1000
  final String label;
  // Shrink factor (0.0 = no shrink, 0.10 = 10% shrink on each side)
  // Used to compensate for Gemini's tendency to produce slightly oversized boxes.
  final double shrinkFactor;

  BoundingBoxPainter({required this.boundingBox, required this.label, this.shrinkFactor = 0.10});

  @override
  void paint(Canvas canvas, Size size) {
    // ⚠️ CRITICAL FIX: Android raw camera frames are usually rotated 90 degrees (Landscape)
    // relative to the screen (Portrait). Gemini processes the raw frame.
    // Therefore, the bounding box [ymin, xmin, ymax, xmax] from Gemini 
    // needs to map its X to the screen's Y, and its Y to the screen's X.
    
    // Normalization (0-1000) mapped to the swapped axes to match portrait display
    double ymin = (boundingBox[1] / 1000.0) * size.height; // Gemini X -> Screen Y
    double xmin = (boundingBox[0] / 1000.0) * size.width;  // Gemini Y -> Screen X
    double ymax = (boundingBox[3] / 1000.0) * size.height; // Gemini X -> Screen Y
    double xmax = (boundingBox[2] / 1000.0) * size.width;  // Gemini Y -> Screen X

    // Apply shrink factor to compensate for Gemini's inflated boxes.
    // Each side is moved inward by (shrinkFactor * box_dimension).
    final dx = (xmax - xmin) * shrinkFactor;
    final dy = (ymax - ymin) * shrinkFactor;
    xmin += dx;
    xmax -= dx;
    ymin += dy;
    ymax -= dy;

    final rect = Rect.fromLTRB(xmin, ymin, xmax, ymax);

    // Draw the flashing/red box
    final paintBox = Paint()
      ..color = Colors.redAccent.withOpacity(0.8)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4.0;

    // Draw slightly rounded rectangle
    canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(8)), paintBox);

    // Draw background for the label
    final textStyle = const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold);
    final textSpan = TextSpan(text: label.toUpperCase(), style: textStyle);
    final textPainter = TextPainter(text: textSpan, textDirection: TextDirection.ltr);
    textPainter.layout();

    final labelBgRect = Rect.fromLTWH(xmin, ymin - textPainter.height - 4, textPainter.width + 8, textPainter.height + 4);
    final paintBg = Paint()..color = Colors.redAccent.withOpacity(0.9);
    canvas.drawRect(labelBgRect, paintBg);

    // Draw the label text
    textPainter.paint(canvas, Offset(xmin + 4, ymin - textPainter.height - 2));
  }

  @override
  bool shouldRepaint(covariant BoundingBoxPainter oldDelegate) {
    return boundingBox != oldDelegate.boundingBox || label != oldDelegate.label || shrinkFactor != oldDelegate.shrinkFactor;
  }
}

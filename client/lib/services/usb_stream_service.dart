import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

enum ConnectionStateStatus { disconnected, connecting, connected, error }

class UsbStreamService extends ChangeNotifier {
  WebSocketChannel? _channel;
  ConnectionStateStatus _status = ConnectionStateStatus.disconnected;
  String _errorMessage = '';

  Uint8List? _latestFrame;
  Map<String, dynamic>? _serverInfo;
  
  // Stats
  double _fps = 0.0;
  final List<int> _frameTimestamps = [];
  Timer? _fpsTimer;
  final ValueNotifier<double> fpsNotifier = ValueNotifier<double>(0.0);

  // Stream controller for frame updates
  final StreamController<Uint8List> _frameStreamController = StreamController<Uint8List>.broadcast();

  String? _lastUrl;

  ConnectionStateStatus get status => _status;
  String get errorMessage => _errorMessage;
  String? get lastUrl => _lastUrl;
  Uint8List? get latestFrame => _latestFrame;
  Map<String, dynamic>? get serverInfo => _serverInfo;
  double get fps => _fps;
  Stream<Uint8List> get frameStream => _frameStreamController.stream;

  void reconnect() {
    if (_lastUrl != null && _status != ConnectionStateStatus.connecting && _status != ConnectionStateStatus.connected) {
      connect(_lastUrl!);
    }
  }

  void connect(String url) {
    if (_status == ConnectionStateStatus.connecting || _status == ConnectionStateStatus.connected) {
      return;
    }

    _lastUrl = url;
    _status = ConnectionStateStatus.connecting;
    _errorMessage = '';
    notifyListeners();

    try {
      final uri = Uri.parse(url);
      _channel = WebSocketChannel.connect(uri);

      _frameTimestamps.clear();
      _fps = 0.0;
      fpsNotifier.value = 0.0;
      _fpsTimer?.cancel();
      _fpsTimer = Timer.periodic(const Duration(milliseconds: 500), (timer) {
        final now = DateTime.now().millisecondsSinceEpoch;
        _frameTimestamps.removeWhere((t) => now - t > 1000);
        final currentFps = _frameTimestamps.length.toDouble();
        _fps = currentFps;
        fpsNotifier.value = currentFps;
        notifyListeners();
      });

      _channel!.stream.listen(
        (message) {
          if (_status != ConnectionStateStatus.connected) {
            _status = ConnectionStateStatus.connected;
            notifyListeners();
          }

          final now = DateTime.now().millisecondsSinceEpoch;
          _frameTimestamps.add(now);

          if (message is Uint8List) {
            _latestFrame = message;
            _frameStreamController.add(message);
          } else if (message is List<int>) {
            final bytes = Uint8List.fromList(message);
            _latestFrame = bytes;
            _frameStreamController.add(bytes);
          } else if (message is String) {
            try {
              final data = json.decode(message);
              if (data is Map<String, dynamic>) {
                _serverInfo = data;
                notifyListeners();
              }
            } catch (e) {
              debugPrint('Error parsing text packet: $e');
            }
          }
        },
        onError: (error) {
          _status = ConnectionStateStatus.error;
          _errorMessage = error.toString();
          _fpsTimer?.cancel();
          _frameTimestamps.clear();
          _fps = 0.0;
          fpsNotifier.value = 0.0;
          notifyListeners();
        },
        onDone: () {
          _status = ConnectionStateStatus.disconnected;
          _fpsTimer?.cancel();
          _frameTimestamps.clear();
          _fps = 0.0;
          fpsNotifier.value = 0.0;
          notifyListeners();
        },
      );
    } catch (e) {
      _status = ConnectionStateStatus.error;
      _errorMessage = e.toString();
      _fpsTimer?.cancel();
      _frameTimestamps.clear();
      _fps = 0.0;
      fpsNotifier.value = 0.0;
      notifyListeners();
    }
  }

  void disconnect() {
    _fpsTimer?.cancel();
    _frameTimestamps.clear();
    _fps = 0.0;
    fpsNotifier.value = 0.0;
    _channel?.sink.close();
    _channel = null;
    _status = ConnectionStateStatus.disconnected;
    _latestFrame = null;
    notifyListeners();
  }

  void sendEvent(Map<String, dynamic> event) {
    if (_status == ConnectionStateStatus.connected && _channel != null) {
      try {
        _channel!.sink.add(json.encode(event));
      } catch (e) {
        debugPrint('Error sending event: $e');
      }
    }
  }

  void sendPointerDown(double x, double y, {String button = 'left'}) {
    sendEvent({'type': 'pointer_down', 'x': x, 'y': y, 'button': button});
  }

  void sendPointerMove(double x, double y) {
    sendEvent({'type': 'pointer_move', 'x': x, 'y': y});
  }

  void sendMouseMove(double dx, double dy, {double speed = 1.5}) {
    sendEvent({'type': 'mouse_move', 'dx': dx, 'dy': dy, 'speed': speed});
  }

  void sendPointerUp(double x, double y, {String button = 'left'}) {
    sendEvent({'type': 'pointer_up', 'x': x, 'y': y, 'button': button});
  }

  void sendTap(double x, double y) {
    sendEvent({'type': 'tap', 'x': x, 'y': y});
  }

  void sendRightTap(double x, double y) {
    sendEvent({'type': 'right_tap', 'x': x, 'y': y});
  }

  void sendDoubleTap(double x, double y) {
    sendEvent({'type': 'double_tap', 'x': x, 'y': y});
  }

  void sendScroll(int dy) {
    sendEvent({'type': 'scroll', 'dy': dy});
  }

  void sendConfig({int? fps, int? quality, double? scale, int? monitorIndex, double? speed}) {
    final Map<String, dynamic> config = {'type': 'config'};
    if (fps != null) config['fps'] = fps;
    if (quality != null) config['quality'] = quality;
    if (scale != null) config['scale'] = scale;
    if (monitorIndex != null) config['monitor_index'] = monitorIndex;
    if (speed != null) config['speed'] = speed;
    sendEvent(config);
  }

  @override
  void dispose() {
    disconnect();
    _frameStreamController.close();
    super.dispose();
  }
}

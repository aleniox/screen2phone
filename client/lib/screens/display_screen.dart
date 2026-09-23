import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import '../services/usb_stream_service.dart';

class DisplayScreen extends StatefulWidget {
  final UsbStreamService streamService;

  const DisplayScreen({super.key, required this.streamService});

  @override
  State<DisplayScreen> createState() => _DisplayScreenState();
}

class _DisplayScreenState extends State<DisplayScreen> {
  final GlobalKey _imageContainerKey = GlobalKey();
  bool _showOverlay = false;
  bool _isLandscape = true;
  int _activeMonitor = 2;
  int _quality = 70;
  int _targetFps = 60;
  int _pointerCount = 0;
  double _lastTwoFingerY = 0.0;
  BoxFit _boxFit = BoxFit.contain; // Default to natural aspect ratio (no stretch)
  bool _enableTouch = true; // Enabled by default
  bool _isTouchpadMode = true; // Trackpad mode with customizable speed
  double _mouseSpeed = 1.5; // Mouse speed multiplier (1.0x - 3.5x)
  DateTime _lastMoveTime = DateTime.now();
  Timer? _reconnectTimer;

  @override
  void initState() {
    super.initState();
    final info = widget.streamService.serverInfo;
    if (info != null && info['active_monitor'] != null) {
      _activeMonitor = (info['active_monitor'] as num).toInt();
    }
    widget.streamService.addListener(_onServiceStatusChanged);
    // Enable immersive sticky full-screen mode
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
    _setOrientation(_isLandscape);
    WakelockPlus.enable();
  }

  void _onServiceStatusChanged() {
    if (!mounted) return;
    if (widget.streamService.status == ConnectionStateStatus.connected) {
      _reconnectTimer?.cancel();
      _reconnectTimer = null;
      final info = widget.streamService.serverInfo;
      if (info != null && info['active_monitor'] != null) {
        _activeMonitor = (info['active_monitor'] as num).toInt();
      }
      setState(() {});
    } else if (widget.streamService.status == ConnectionStateStatus.disconnected ||
               widget.streamService.status == ConnectionStateStatus.error) {
      _reconnectTimer ??= Timer.periodic(const Duration(seconds: 2), (timer) {
        if (mounted && widget.streamService.status != ConnectionStateStatus.connected) {
          widget.streamService.reconnect();
        }
      });
      setState(() {});
    }
  }

  void _setOrientation(bool landscape) {
    if (landscape) {
      SystemChrome.setPreferredOrientations([
        DeviceOrientation.landscapeLeft,
        DeviceOrientation.landscapeRight,
      ]);
    } else {
      SystemChrome.setPreferredOrientations([
        DeviceOrientation.portraitUp,
        DeviceOrientation.portraitDown,
      ]);
    }
  }

  @override
  void dispose() {
    _reconnectTimer?.cancel();
    widget.streamService.removeListener(_onServiceStatusChanged);
    WakelockPlus.disable();
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp,
      DeviceOrientation.portraitDown,
      DeviceOrientation.landscapeLeft,
      DeviceOrientation.landscapeRight,
    ]);
    super.dispose();
  }

  Offset? _getNormalizedOffset(Offset localPosition) {
    final RenderBox? box = _imageContainerKey.currentContext?.findRenderObject() as RenderBox?;
    if (box == null || box.size.width == 0 || box.size.height == 0) return null;

    if (_boxFit == BoxFit.fill) {
      final double normX = (localPosition.dx / box.size.width).clamp(0.0, 1.0);
      final double normY = (localPosition.dy / box.size.height).clamp(0.0, 1.0);
      return Offset(normX, normY);
    }

    // BoxFit.contain mapping
    final serverRect = widget.streamService.serverInfo?['rect'];
    final double pcW = (serverRect != null && serverRect['width'] != null)
        ? (serverRect['width'] as num).toDouble()
        : 1920.0;
    final double pcH = (serverRect != null && serverRect['height'] != null)
        ? (serverRect['height'] as num).toDouble()
        : 1080.0;
    final double pcRatio = (pcW > 0 && pcH > 0) ? (pcW / pcH) : (16.0 / 9.0);
    final double screenRatio = box.size.width / box.size.height;

    double renderW, renderH, offsetX, offsetY;
    if (screenRatio > pcRatio) {
      renderH = box.size.height;
      renderW = renderH * pcRatio;
      offsetX = (box.size.width - renderW) / 2.0;
      offsetY = 0.0;
    } else {
      renderW = box.size.width;
      renderH = renderW / pcRatio;
      offsetX = 0.0;
      offsetY = (box.size.height - renderH) / 2.0;
    }

    if (localPosition.dx < offsetX ||
        localPosition.dx > offsetX + renderW ||
        localPosition.dy < offsetY ||
        localPosition.dy > offsetY + renderH) {
      return null;
    }

    final double normX = ((localPosition.dx - offsetX) / renderW).clamp(0.0, 1.0);
    final double normY = ((localPosition.dy - offsetY) / renderH).clamp(0.0, 1.0);
    return Offset(normX, normY);
  }

  void _onPointerDown(PointerDownEvent event) {
    if (!_enableTouch) return;
    _pointerCount++;
    if (_pointerCount == 2) {
      _lastTwoFingerY = event.position.dy;
    } else if (_pointerCount == 1) {
      if (!_isTouchpadMode) {
        final norm = _getNormalizedOffset(event.localPosition);
        if (norm != null) {
          widget.streamService.sendPointerDown(norm.dx, norm.dy, button: 'left');
        }
      }
    }
  }

  void _onPointerMove(PointerMoveEvent event) {
    if (!_enableTouch) return;
    if (_pointerCount == 2) {
      // Two-finger scroll
      final double deltaY = event.position.dy - _lastTwoFingerY;
      if (deltaY.abs() > 8) {
        final int scrollAmount = deltaY > 0 ? 1 : -1;
        widget.streamService.sendScroll(scrollAmount);
        _lastTwoFingerY = event.position.dy;
      }
    } else if (_pointerCount == 1) {
      final now = DateTime.now();
      if (now.difference(_lastMoveTime).inMilliseconds >= 12) {
        _lastMoveTime = now;
        if (_isTouchpadMode) {
          widget.streamService.sendMouseMove(event.delta.dx, event.delta.dy, speed: _mouseSpeed);
        } else {
          final norm = _getNormalizedOffset(event.localPosition);
          if (norm != null) {
            widget.streamService.sendPointerMove(norm.dx, norm.dy);
          }
        }
      }
    }
  }

  void _onPointerUp(PointerUpEvent event) {
    if (!_enableTouch) return;
    _pointerCount = (_pointerCount - 1).clamp(0, 10);
    if (_pointerCount == 0) {
      if (!_isTouchpadMode) {
        final norm = _getNormalizedOffset(event.localPosition);
        if (norm != null) {
          widget.streamService.sendPointerUp(norm.dx, norm.dy, button: 'left');
        }
      }
    }
  }

  void _onSecondaryTap(TapUpDetails details) {
    if (!_enableTouch) return;
    if (_isTouchpadMode) {
      widget.streamService.sendRightTap(0, 0);
    } else {
      final norm = _getNormalizedOffset(details.localPosition);
      if (norm != null) {
        widget.streamService.sendRightTap(norm.dx, norm.dy);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // Main Screen Stream Display
          SizedBox.expand(
            key: _imageContainerKey,
            child: Listener(
              onPointerDown: _onPointerDown,
              onPointerMove: _onPointerMove,
              onPointerUp: _onPointerUp,
              child: GestureDetector(
                onSecondaryTapUp: _onSecondaryTap,
                child: RepaintBoundary(
                  child: StreamBuilder<Uint8List>(
                    stream: widget.streamService.frameStream,
                    initialData: widget.streamService.latestFrame,
                    builder: (context, snapshot) {
                      if (snapshot.hasData && snapshot.data != null && snapshot.data!.isNotEmpty) {
                        return Image.memory(
                          snapshot.data!,
                          gaplessPlayback: true,
                          fit: _boxFit,
                          width: double.infinity,
                          height: double.infinity,
                          errorBuilder: (context, error, stackTrace) {
                            return const Center(
                              child: Text(
                                "Đang đồng bộ hình ảnh...",
                                style: TextStyle(color: Colors.white60),
                              ),
                            );
                          },
                        );
                      }
                      return const Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            CircularProgressIndicator(color: Colors.blueAccent),
                            SizedBox(height: 16),
                            Text(
                              "Đang chờ hình ảnh từ máy tính...",
                              style: TextStyle(color: Colors.white70, fontSize: 16),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
              ),
            ),
          ),

          // Reconnecting Overlay if Server disconnected / restarting
          if (widget.streamService.status != ConnectionStateStatus.connected)
            Positioned.fill(
              child: Container(
                color: Colors.black.withAlpha(200),
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const SizedBox(
                        width: 44,
                        height: 44,
                        child: CircularProgressIndicator(
                          color: Colors.blueAccent,
                          strokeWidth: 3,
                        ),
                      ),
                      const SizedBox(height: 18),
                      const Text(
                        "Mất kết nối với Máy tính",
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        "Đang tự động kết nối lại...\n(Server đang đổi cấu hình hoặc khởi động lại)",
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.white70, fontSize: 13),
                      ),
                      const SizedBox(height: 20),
                      ElevatedButton.icon(
                        icon: const Icon(Icons.arrow_back, size: 16),
                        label: const Text("Quay lại"),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.white24,
                          foregroundColor: Colors.white,
                        ),
                        onPressed: () {
                          _reconnectTimer?.cancel();
                          widget.streamService.disconnect();
                          Navigator.of(context).pop();
                        },
                      ),
                    ],
                  ),
                ),
              ),
            ),

          // Floating Live FPS Badge (Top Left)
          Positioned(
            top: 16,
            left: 16,
            child: SafeArea(
              child: ValueListenableBuilder<double>(
                valueListenable: widget.streamService.fpsNotifier,
                builder: (context, fps, _) {
                  final color = fps >= 45
                      ? Colors.greenAccent
                      : (fps >= 25 ? Colors.amberAccent : Colors.redAccent);
                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.black.withAlpha(190),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: color.withAlpha(140), width: 1),
                      boxShadow: const [
                        BoxShadow(color: Colors.black45, blurRadius: 4),
                      ],
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: color,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          "${fps.toStringAsFixed(0)} FPS",
                          style: TextStyle(
                            color: color,
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ),

          // Floating Toggle Menu Button (Top Right)
          Positioned(
            top: 16,
            right: 16,
            child: SafeArea(
              child: RepaintBoundary(
                child: Opacity(
                  opacity: _showOverlay ? 1.0 : 0.4,
                  child: FloatingActionButton.small(
                    backgroundColor: Colors.black87,
                    foregroundColor: Colors.white,
                    onPressed: () {
                      setState(() {
                        _showOverlay = !_showOverlay;
                      });
                    },
                    child: Icon(_showOverlay ? Icons.close : Icons.tune),
                  ),
                ),
              ),
            ),
          ),

          // Overlay Control Panel
          if (_showOverlay)
            Positioned(
              top: 56,
              right: 16,
              bottom: 16,
              child: SafeArea(
                child: Container(
                  width: 300,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: Colors.black.withAlpha(235),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.white24),
                    boxShadow: const [
                      BoxShadow(color: Colors.black87, blurRadius: 12, spreadRadius: 2),
                    ],
                  ),
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              "Tùy chỉnh màn hình",
                              style: TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 15,
                              ),
                            ),
                          ],
                        ),
                      const Divider(color: Colors.white24, height: 20),

                      // Monitor Selection
                      const Text("Màn hình hiển thị:", style: TextStyle(color: Colors.white70, fontSize: 13)),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          Expanded(
                            child: ChoiceChip(
                              label: const Text("Màn hình 1"),
                              selected: _activeMonitor == 1,
                              onSelected: (val) {
                                if (val && _activeMonitor != 1) {
                                  setState(() => _activeMonitor = 1);
                                  widget.streamService.sendConfig(monitorIndex: 1);
                                }
                              },
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: ChoiceChip(
                              label: const Text("Màn hình 2"),
                              selected: _activeMonitor == 2,
                              onSelected: (val) {
                                if (val && _activeMonitor != 2) {
                                  setState(() => _activeMonitor = 2);
                                  widget.streamService.sendConfig(monitorIndex: 2);
                                }
                              },
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),

                      // Aspect Ratio Mode
                      const Text("Tỉ lệ hiển thị:", style: TextStyle(color: Colors.white70, fontSize: 13)),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          Expanded(
                            child: ChoiceChip(
                              label: const Text("Chuẩn 16:9"),
                              selected: _boxFit == BoxFit.contain,
                              onSelected: (val) {
                                setState(() => _boxFit = BoxFit.contain);
                              },
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: ChoiceChip(
                              label: const Text("Tràn viền"),
                              selected: _boxFit == BoxFit.fill,
                              onSelected: (val) {
                                setState(() => _boxFit = BoxFit.fill);
                              },
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),

                      // Touch Input Toggle
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        dense: true,
                        title: const Text("Cảm ứng màn hình", style: TextStyle(color: Colors.white70, fontSize: 13)),
                        subtitle: Text(
                          _enableTouch ? "Đang Bật (Chạm / di chuột)" : "Đang Tắt (Chỉ dùng chuột PC)",
                          style: TextStyle(color: _enableTouch ? Colors.greenAccent : Colors.white38, fontSize: 11),
                        ),
                        value: _enableTouch,
                        onChanged: (val) {
                          setState(() => _enableTouch = val);
                        },
                      ),
                      if (_enableTouch) ...[
                        const SizedBox(height: 4),
                        const Text("Kiểu điều khiển chuột:", style: TextStyle(color: Colors.white70, fontSize: 13)),
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            Expanded(
                              child: ChoiceChip(
                                label: const Text("Bàn rê (Trackpad)"),
                                selected: _isTouchpadMode,
                                onSelected: (val) {
                                  if (val) setState(() => _isTouchpadMode = true);
                                },
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: ChoiceChip(
                                label: const Text("Chạm trực tiếp"),
                                selected: !_isTouchpadMode,
                                onSelected: (val) {
                                  if (val) setState(() => _isTouchpadMode = false);
                                },
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          "Tốc độ chuột: ${_mouseSpeed.toStringAsFixed(1)}x",
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                        Slider(
                          value: _mouseSpeed.clamp(0.5, 3.5),
                          min: 0.5,
                          max: 3.5,
                          divisions: 6,
                          label: "${_mouseSpeed.toStringAsFixed(1)}x",
                          onChanged: (val) {
                            setState(() => _mouseSpeed = val);
                          },
                          onChangeEnd: (val) {
                            widget.streamService.sendConfig(speed: val);
                          },
                        ),
                      ],
                      const SizedBox(height: 8),

                      // Quality Selection
                      Text("Chất lượng ảnh: $_quality%", style: const TextStyle(color: Colors.white70, fontSize: 13)),
                      Slider(
                        value: _quality.toDouble().clamp(30.0, 80.0),
                        min: 30,
                        max: 80,
                        divisions: 10,
                        label: "$_quality%",
                        onChanged: (val) {
                          setState(() => _quality = val.toInt());
                        },
                        onChangeEnd: (val) {
                          widget.streamService.sendConfig(quality: val.toInt());
                        },
                      ),

                      // FPS Selection
                      const Text("FPS Mục tiêu:", style: TextStyle(color: Colors.white70, fontSize: 13)),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [30, 60].map((fps) {
                          return ChoiceChip(
                            label: Text("$fps FPS"),
                            selected: _targetFps == fps,
                            onSelected: (val) {
                              setState(() => _targetFps = fps);
                              widget.streamService.sendConfig(fps: fps);
                            },
                          );
                        }).toList(),
                      ),
                      const SizedBox(height: 12),

                      // Rotation & Disconnect
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              icon: const Icon(Icons.screen_rotation, size: 18),
                              label: Text(_isLandscape ? "Dọc" : "Ngang"),
                              style: OutlinedButton.styleFrom(foregroundColor: Colors.white),
                              onPressed: () {
                                setState(() {
                                  _isLandscape = !_isLandscape;
                                  _setOrientation(_isLandscape);
                                });
                              },
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: ElevatedButton.icon(
                              icon: const Icon(Icons.power_settings_new, size: 18),
                              label: const Text("Ngắt"),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.redAccent,
                                foregroundColor: Colors.white,
                              ),
                              onPressed: () {
                                widget.streamService.disconnect();
                                Navigator.of(context).pop();
                              },
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

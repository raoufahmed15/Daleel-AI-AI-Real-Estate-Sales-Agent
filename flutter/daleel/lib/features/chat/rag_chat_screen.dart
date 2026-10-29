import 'dart:async';
import 'dart:typed_data';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:record/record.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';

class _ChatEntry {
  const _ChatEntry({
    required this.isUser,
    required this.text,
    this.sources = const [],
    this.handoffReason,
  });

  final bool isUser;
  final String text;
  final List<RagSource> sources;
  final String? handoffReason;
}

class RagChatScreen extends ConsumerStatefulWidget {
  const RagChatScreen({super.key});

  @override
  ConsumerState<RagChatScreen> createState() => _RagChatScreenState();
}

class _RagChatScreenState extends ConsumerState<RagChatScreen> {
  final _messageController = TextEditingController();
  final _scrollController = ScrollController();
  final _recorder = AudioRecorder();
  final _audioBytes = BytesBuilder(copy: false);
  late String _sessionId;
  late List<_ChatEntry> _messages;
  StreamSubscription<Uint8List>? _audioSubscription;
  Timer? _recordingLimit;
  bool _busy = false;
  bool _recording = false;
  bool _transcribing = false;

  String get _greeting {
    final isArabic = Localizations.localeOf(context).languageCode == 'ar';
    return isArabic
        ? 'أهلًا بك! أنا مساعد دليل العقاري. اسألني عن الوحدات والأسعار والتوافر وخطط السداد، وسأجيبك من المصادر المعتمدة.'
        : 'Welcome! I am Daleel’s real-estate assistant. Ask about units, prices, availability, or payment plans. I answer using approved sources.';
  }

  @override
  void initState() {
    super.initState();
    _sessionId = _newSessionId();
    _messages = const [];
  }

  String _newSessionId() =>
      '${DateTime.now().microsecondsSinceEpoch}_${Random.secure().nextInt(0x7fffffff).toRadixString(16)}';

  @override
  void dispose() {
    _recordingLimit?.cancel();
    unawaited(_audioSubscription?.cancel());
    unawaited(_recorder.dispose());
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _toggleRecording() async {
    if (_recording) {
      await _stopRecording();
      return;
    }
    if (_busy || _transcribing) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.tr('voice_privacy_title')),
        content: Text(context.tr('voice_privacy_notice')),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(context.tr('cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(context.tr('voice_continue')),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    try {
      if (!await _recorder.hasPermission()) {
        if (mounted) {
          snack(context, context.tr('microphone_permission_denied'),
              error: true);
        }
        return;
      }
      _audioBytes.clear();
      final stream = await _recorder.startStream(const RecordConfig(
        encoder: AudioEncoder.pcm16bits,
        sampleRate: 16000,
        numChannels: 1,
        echoCancel: true,
        noiseSuppress: true,
      ));
      _audioSubscription = stream.listen(
        _audioBytes.add,
        onError: (Object error, StackTrace stack) {
          if (mounted) snack(context, error.toString(), error: true);
        },
      );
      if (!mounted) {
        await _recorder.cancel();
        return;
      }
      setState(() => _recording = true);
      _recordingLimit = Timer(
        const Duration(seconds: 45),
        _stopRecording,
      );
    } catch (error) {
      if (mounted) {
        snack(context, '${context.tr('recording_failed')}: $error',
            error: true);
      }
    }
  }

  Future<void> _stopRecording() async {
    if (!_recording) return;
    _recordingLimit?.cancel();
    _recordingLimit = null;
    if (!mounted) return;
    final emptyRecordingMessage = context.tr('empty_recording');
    setState(() {
      _recording = false;
      _transcribing = true;
    });

    try {
      await _recorder.stop();
      final audioSubscription = _audioSubscription;
      _audioSubscription = null;
      await audioSubscription?.cancel();
      final pcm = _audioBytes.takeBytes();
      if (pcm.isEmpty) {
        throw StateError(emptyRecordingMessage);
      }
      final transcript = await ref
          .read(repoProvider)
          .transcribeAudio(_wavBytes(pcm, sampleRate: 16000));
      if (!mounted) return;
      _messageController.text = transcript;
      _messageController.selection = TextSelection.collapsed(
        offset: transcript.length,
      );
      snack(context, context.tr('transcription_ready'));
    } catch (error) {
      if (mounted) {
        snack(context, '${context.tr('transcription_failed')}: $error',
            error: true);
      }
    } finally {
      if (mounted) setState(() => _transcribing = false);
    }
  }

  Uint8List _wavBytes(Uint8List pcm, {required int sampleRate}) {
    final bytes = ByteData(44 + pcm.length);
    void writeAscii(int offset, String value) {
      for (var i = 0; i < value.length; i++) {
        bytes.setUint8(offset + i, value.codeUnitAt(i));
      }
    }

    writeAscii(0, 'RIFF');
    bytes.setUint32(4, 36 + pcm.length, Endian.little);
    writeAscii(8, 'WAVE');
    writeAscii(12, 'fmt ');
    bytes.setUint32(16, 16, Endian.little);
    bytes.setUint16(20, 1, Endian.little);
    bytes.setUint16(22, 1, Endian.little);
    bytes.setUint32(24, sampleRate, Endian.little);
    bytes.setUint32(28, sampleRate * 2, Endian.little);
    bytes.setUint16(32, 2, Endian.little);
    bytes.setUint16(34, 16, Endian.little);
    writeAscii(36, 'data');
    bytes.setUint32(40, pcm.length, Endian.little);
    bytes.buffer.asUint8List().setRange(44, 44 + pcm.length, pcm);
    return bytes.buffer.asUint8List();
  }

  void _startNewChat() {
    if (_busy) return;
    setState(() {
      _sessionId = _newSessionId();
      _messages = [];
    });
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty || _busy) return;

    _messageController.clear();
    setState(() {
      _busy = true;
      _messages = [..._messages, _ChatEntry(isUser: true, text: text)];
    });
    _scrollToBottom();

    try {
      final answer = await ref.read(repoProvider).askRag(text, _sessionId);
      if (!mounted) return;
      setState(() {
        _messages = [
          ..._messages,
          _ChatEntry(
            isUser: false,
            text: answer.reply,
            sources: answer.sources,
            handoffReason: answer.reason,
          ),
        ];
      });
      _scrollToBottom();
    } catch (error) {
      if (mounted) snack(context, error.toString(), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isArabic = Localizations.localeOf(context).languageCode == 'ar';
    final messages = _messages.isEmpty
        ? [_ChatEntry(isUser: false, text: _greeting)]
        : _messages;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: PageHeader(context.tr('nav_chat'))),
            IconButton(
              tooltip: context.tr('new_chat'),
              onPressed: _busy ? null : _startNewChat,
              icon: const Icon(Icons.add_comment_outlined),
            ),
          ],
        ),
        Expanded(
          child: ListView.builder(
            controller: _scrollController,
            padding: const EdgeInsets.symmetric(vertical: 8),
            itemCount: messages.length + (_busy ? 1 : 0),
            itemBuilder: (context, index) {
              if (_busy && index == messages.length) {
                return Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                  ),
                );
              }
              return _MessageBubble(entry: messages[index]);
            },
          ),
        ),
        const SizedBox(height: 8),
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: TextField(
                controller: _messageController,
                enabled: !_busy && !_recording && !_transcribing,
                minLines: 1,
                maxLines: 4,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _sendMessage(),
                decoration: InputDecoration(
                  hintText:
                      isArabic ? 'اكتب سؤالك هنا...' : 'Ask a question...',
                  border: const OutlineInputBorder(),
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filledTonal(
              tooltip: _recording
                  ? context.tr('stop_recording')
                  : context.tr('record_voice'),
              onPressed: _busy || _transcribing ? null : _toggleRecording,
              style: _recording
                  ? IconButton.styleFrom(
                      foregroundColor: Theme.of(context).colorScheme.error,
                    )
                  : null,
              icon: _transcribing
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Icon(_recording ? Icons.stop : Icons.mic_none),
            ),
            const SizedBox(width: 4),
            IconButton.filled(
              tooltip: context.tr('send_message'),
              onPressed:
                  _busy || _recording || _transcribing ? null : _sendMessage,
              icon: const Icon(Icons.send),
            ),
          ],
        ),
      ],
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.entry});

  final _ChatEntry entry;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Align(
      alignment: entry.isUser
          ? AlignmentDirectional.centerEnd
          : AlignmentDirectional.centerStart,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 760),
        child: Card(
          color: entry.isUser
              ? colorScheme.primaryContainer
              : colorScheme.surfaceContainerHighest,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SelectableText(entry.text),
                if (entry.handoffReason != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    '${context.tr('human_handoff')}: ${context.tr(entry.handoffReason!)}',
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                ],
                if (entry.sources.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    context.tr('chat_citations'),
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                  for (final source in entry.sources)
                    Text(
                      [
                        source.title.isEmpty ? source.docId : source.title,
                        if (source.version.isNotEmpty) source.version,
                        if (source.issueDate.isNotEmpty) source.issueDate,
                      ].join(' · '),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

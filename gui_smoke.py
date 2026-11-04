"""Actual Tk smoke, offline only; exercises app handlers and worker injection."""
from .app import *
from unittest.mock import patch
import tempfile
from audio_protocol import encode_frame

def run():
    root=tk.Tk();temp=tempfile.TemporaryDirectory(dir=ROOT/'reports')
    app=App(root,hardware_enabled=False,data_folder=Path(temp.name)/'library')
    result=dict(passed=False,scope='Real Tk GUI + offline public train WAV + mock transport; NO COM6/hardware',checks=[],errors=[])
    started=time.monotonic();phase=0;worker_frames=0
    def check():
        nonlocal phase,worker_frames
        try:
            if time.monotonic()-started>50:raise TimeoutError('GUI smoke timeout')
            if phase==0:
                for i in range(9):app.show_page(i);root.update_idletasks();assert app.pages[i].winfo_ismapped()
                result['checks'].append('all_nine_pages')
                for size in ('860x600','1280x820'):
                    root.geometry(size);root.update_idletasks();app.show_page(0);root.update_idletasks()
                    assert app.pages[0].canvas.winfo_width()>500
                    last=app.nav_buttons[-1]
                    assert last.winfo_rooty()+last.winfo_height()<root.winfo_rooty()+root.winfo_height()
                result['checks'].append('responsive_layout_860_and_1280')
                app.show_page(4);app.load_public();phase=1
            elif phase==1:
                if not getattr(app,'latest_prediction',None):root.after(150,check);return
                assert '公开' in app.engine.source and app.worker is None
                assert app.truth.get().startswith('公开数据真实原标签')
                result['checks'].append('public_truth_separate_from_prediction')
                raw=app.engine.raw()[0].copy();app.dc.set(False);app.notch.set(False);app.apply_filters()
                np.testing.assert_array_equal(app.engine.session.filtered_waveform,raw[-4096:]);np.testing.assert_array_equal(app.engine.raw()[0],raw)
                app.dc.set(True);app.notch.set(True);app.harmonic.set(True);app.apply_filters()
                result['checks'].append('filter_toggle_raw_immutable')
                with patch('winsound.PlaySound') as play:
                    app.play(False);assert play.call_count==1
                result['checks'].append('playback_api_mocked_not_audio_device_verified')
                app.add_current_to_library();rid=app.selected_record
                app.annotator.set('Stage7 automated fixture');app.basis.set('测试夹具，不是实测标签');app.event.set('uncertain');app.context.set('unknown');app.ann_start.set('0');app.ann_end.set('.5');app.save_annotation()
                assert len(app.library.annotations(rid))==1
                app.undo_annotation();assert not app.library.annotations(rid)
                result['checks'].append('library_and_human_annotation_undo')
                app.save_audio();assert any('_FILTERED.wav' in p.name for p in app.last_saved)
                result['checks'].append('raw_filtered_wav_export')
                app.model_choice.set(MODEL_NAMES['optimized']);app.change_model();del app.latest_prediction;app.infer();phase=2
            elif phase==2:
                if not getattr(app,'latest_prediction',None):root.after(150,check);return
                assert 'stage6-optimization' in app.model_info.get();result['checks'].append('optimized_model_switch_and_metrics')
                app.choose_model('final');phase=2.5
            elif phase==2.5:
                if not getattr(app,'latest_prediction',None):root.after(150,check);return
                assert 'stage8-context-candidate' in app.model_info.get() and 'Macro Precision' in app.model_info.get()
                result['checks'].append('stage8_candidate_switch_full_cv_metrics')
                app.choose_model('best');phase=2.7
            elif phase==2.7:
                if not getattr(app,'latest_prediction',None):root.after(150,check);return
                assert '稳定选择' in app.model_info.get()
                result['checks'].append('best_entry_obeys_promotion_decision')
                import shutil
                fixture=Path(temp.name)/'UNLABELED_PUBLIC_TEST_FIXTURE.wav'
                shutil.copy2(ROOT/app.catalog[0]['file'],fixture)
                with patch('tkinter.filedialog.askopenfilename',return_value=str(fixture)):app.import_demo_wav()
                phase=2.9
            elif phase==2.9:
                if not getattr(app,'latest_prediction',None):root.after(150,check);return
                assert app.current_public is None and '无人工确认标签' in app.truth.get()
                assert 'accuracy' not in app.latest_prediction
                result['checks'].append('unlabeled_wav_inference_no_accuracy_or_guessed_truth')
                app.demo_filter.set('F');app.filter_public()
                assert all(str(v).startswith('F_') for v in app.public_combo.cget('values'))
                result['checks'].append('public_true_label_filter_not_prediction_selection')
                app.mode.set('模拟链路（测试）');app.start_capture();phase=3
            elif phase==3:
                if app.last_stats.get('valid',0)<6:root.after(100,check);return
                app.stop_capture();assert '模拟数据' in app.engine.source;worker_frames=app.last_stats['valid']
                assert app.current_public is None and '公开数据真实原标签' not in app.truth.get()
                assert app.latest_prediction is None
                result['checks'].append('source_change_clears_old_truth_and_prediction')
                result['checks'].append('simulation_packet_worker_and_wave_fft')
                assert len(app.plots[2].raw_wave.get_ydata())>0 or len(app.engine.session.waveform)>0
                app.mode.set('硬件串口音频')
                try:app.start_capture()
                except ValueError:pass
                else:raise AssertionError('Automation hardware gate failed')
                result['checks'].append('physical_serial_blocked')
                class Broken:
                    def open(self,*a):pass
                    def read(self):raise OSError('INJECTED disconnection')
                    def close(self):self.closed=True
                broken=Broken();app.worker=StreamWorker('audio',serial_factory=lambda:broken);app.worker.start();phase=4
            elif phase==4:
                if not app.worker.error:root.after(100,check);return
                assert 'INJECTED' in app.worker.error and app.worker.snapshot()['valid']==0
                result['checks'].append('injected_disconnect_no_fake_data')
                app.worker=None;app.load_public();app.show_page(2);root.update_idletasks()
                app.plots[2].figure.savefig(ROOT/'reports/offline_analysis_plot.png',dpi=150)
                result.update(passed=True,callback_errors=app.callback_errors,simulation_valid_frames=worker_frames,real_hardware_tested=False,physical_audio_device_tested=False)
                finish();return
            root.after(120,check)
        except Exception as exc:
            result['errors'].append(dict(error=repr(exc),traceback=traceback.format_exc()));finish()
    def finish():
        result['passed']=result['passed'] and not app.callback_errors
        (ROOT/'reports/gui_smoke.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
        app.close();temp.cleanup()
    root.after(200,check);root.mainloop()
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(run())

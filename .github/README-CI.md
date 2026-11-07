# CI сборка RF Online клиента

## Файлы
- `workflows/build.yml` — основной workflow (два job'а):
  - **vc6** — идеальный путь: детектирует Visual C++ 6.0 на раннере, скачивает
    DirectX 8.1 SDK (`scripts/prepare_deps.py`), генерирует NMAKE-макфайлы из
    `.dsp` (`scripts/gen_nmake_makes.py`) и собирает `R3EngineDMT.lib` →
    `RF_Online.bin`. На стандартных GitHub-раннерах VC6 нет, поэтому job
    завершается «skipped/passed» без сборки — для него нужен self-hosted
    runner с установленным VS6 SP6.
  - **msvc-modern** — best-effort: компилирует все 238 .cpp современным cl.exe
    и публикует полный список ошибок совместимости (полезно для порта).
- `scripts/prepare_deps.py` — скачивание/распаковка DX8.1 SDK (+BASS).
- `scripts/gen_nmake_makes.py` — экспорт `.dsp` → nmake makefile.

## Секреты репозитория (опционально)
| Secret | Назначение |
|---|---|
| `DX81SDK_URL` | прямая ссылка на `dx81sdk.exe`, если зеркала Microsoft недоступны |

## Required артефакты, которых нет в репо
- заголовки/либы DirectX 8.1 SDK (скачивает prepare_deps.py);
- `mss32.lib` Miles Sound System — проприетарный, только вручную;
- DLL из `Bin/` не нужны для компиляции, но нужны для запуска.

## Self-hosted runner для полной сборки
```
runner labels: rf-build   # затем поменяйте runs-on: [self-hosted, windows, rf-build]
```
На машине: Windows + VC6 SP6 + dx81sdk (можно положить в `_deps/`).

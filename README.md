<p>
  <a href="https://mcas.uos.ac.kr"><img src="assets/mcaslab.png" alt="MCAS Lab" height="34"></a>
  &nbsp;&nbsp;
  <a href="https://www.uos.ac.kr"><img src="assets/uos.png" alt="University of Seoul" height="20"></a>
</p>

# Wireline Census

ISSCC, VLSI, JSSC, CICC, ESSCIRC/ESSERC, A-SSCC, SSC-L, TCAS-I/II, TVLSI에 실린 유선(wireline) 송수신기 논문을 모아 보여주는 사이트입니다. 특히 **ADC/DAC 기반**과 **DSP 기반** 송수신기를 따로 걸러 볼 수 있습니다. 키워드는 김가인 교수님의 제안(PAM4, DFE, MLSD, 112 GS/s, ADC-based)을 반영했습니다. MCAS Lab(서울시립대학교 첨단융합학부)에서 운영합니다.

- 사이트: https://mixedcas-lab.github.io/wireline-census/
- 데이터 출처: IEEE Xplore API (서지 메타데이터와 링크만 공개, 초록·본문은 올리지 않음)

## 동작 방식

1. **데이터**: adc-census 수집기가 받아 둔 랩 서버 캐시(`~/adc-census/cache/raw`)를 읽기만 합니다. IEEE API를 따로 쓰지 않습니다.
2. **분류**: 제목에 송수신기·수신기·송신기·SerDes·CDR·등화기(DFE/FFE/CTLE/MLSD)·TIA 등과 유선 맥락(Gb/s, PAM, NRZ, SerDes, backplane, die-to-die, HBM/GDDR, 광 링크 등)이 함께 있으면 core입니다. 무선(RF, mm-wave, 6G, 안테나, 베이스밴드)은 제외합니다.
3. **유형** (제목과 초록 앞 두 문장 기준): **ADC/DAC-based**(검출 전에 ADC로 디지털화하는 수신기 또는 DAC로 파형을 만드는 송신기, 보통 뒤에 DSP), **DSP (no ADC)**(디지털 등화·MLSD·DMT 등을 쓰지만 ADC/DAC 앞단을 내세우지 않는 경우), **Analog/mixed-signal**(그 외).
4. **태그**: 구조(ADC-based RX, DAC-based TX, MLSD, DFE, FFE, CTLE, CDR, DMT, 크로스토크/에코 제거, clock-forwarded, FEC), 변조(NRZ, PAM3/4/6/8, duobinary, DMT/OFDM), 응용(장거리/백플레인, 광/데이터센터, die-to-die, 메모리, PCIe/Ethernet/USB, 디스플레이/차량).
5. **수치**: 데이터 속도, 에너지 효율(pJ/b), 채널 손실(dB), BER, ADC/DAC 샘플링 속도·분해능, 전력, 공정, 면적. 제목 값을 우선하고, 초록에 같은 항목의 값이 여럿이면 비워 둡니다. pJ/b가 없으면 전력/속도로 계산합니다(≈ 표시).
6. **공개**: cron이 매일 06:37에 재생성하고, 바뀐 것이 있으면 커밋·push합니다.

## 그래프

pJ/b vs. 데이터 속도, 채널 손실 vs. 데이터 속도, pJ/b vs. 채널 손실, 연도별 데이터 속도, pJ/b vs. 공정, ADC/DAC 샘플링 속도 vs. 데이터 속도, Custom.

## 검수 값 넣기

GitHub 웹에서 `data/annotations.csv`를 편집합니다. 열: `id, exclude, type, arch, app, mod, rate(b/s), eff(pJ/b), loss(dB), ber(log10), fsadc(S/s), resadc(bit), p(W), node(nm), area(mm²), cal, note, by`. `-`는 값 삭제입니다.

## 랩 서버 설정 (1회)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/wireline_census -N "" -C "wireline-census@lab-server"   # 공개키를 Deploy keys에 쓰기 권한으로 등록
git clone github-wireline-census:mixedcas-lab/wireline-census.git ~/wireline-census
( crontab -l; echo "37 6 * * * PYTHON=$(command -v python3) $HOME/wireline-census/scripts/update.sh >> $HOME/wireline-census/logs/update.log 2>&1" ) | crontab -
```

GitHub Pages: Settings → Pages에서 Branch를 **main / (root)**로 지정합니다.

/* [2-1] 하나 AI 학원 웹 상호작용 */

// [3-3] 모든 페이지에 채팅 UI 자동 생성
function initializeChatUI() {
  // 이미 있으면 스킵
  if (document.getElementById('chatModal')) return;

  // 채팅 모달 생성
  const chatModalHtml = `
    <div class="chat-modal" id="chatModal">
      <div class="chat-container">
        <div class="chat-header">
          <div class="chat-title-box">
            <img src="assets/mark.png" alt="하나봇" class="chat-icon">
            <span class="chat-title">하나봇</span>
          </div>
          <button class="chat-close" id="chatClose">✕</button>
        </div>
        <div class="chat-messages" id="chatMessages">
          <div class="chat-message bot">
            <img src="assets/brand/app_icon.png" alt="하나 AI 채팅봇" style="width: 40px; height: 40px; border-radius: 8px; margin-right: 10px; vertical-align: middle;">
            <div class="message-content" style="display: inline-block; vertical-align: middle;">안녕하세요! 하나 AI 학원 규정을 물어보세요.</div>
          </div>
        </div>
        <div class="chat-input-area">
          <input type="text" class="chat-input" id="chatInput" placeholder="질문을 입력하세요..." autocomplete="off">
          <button class="chat-send" id="chatSend">전송</button>
        </div>
      </div>
    </div>
  `;

  // 떠 있는 버튼 생성
  const floatingButtonsHtml = `
    <div class="floating-buttons">
      <button class="float-btn main-btn" id="floatHanabot" title="하나봇에게 묻기">
        <img src="assets/mark.png" alt="하나봇">
      </button>
      <button class="float-btn" id="floatConsult" title="상담 신청">📞</button>
      <button class="float-btn" id="floatFaq" title="FAQ">❓</button>
      <button class="float-btn" id="floatTop" title="맨 위로">⬆️</button>
    </div>
  `;

  // HTML 추가
  document.body.insertAdjacentHTML('beforeend', chatModalHtml);
  document.body.insertAdjacentHTML('beforeend', floatingButtonsHtml);
}

// [3-3] 초기화 시 UI 생성
initializeChatUI();

// [3-3] 마크다운을 HTML로 변환
function markdownToHtml(text) {
  if (!text) return '';
  // ** 굵게 ** → <strong>
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // - 목록 → • (단락 내)
  text = text.replace(/^- /gm, '• ');
  // \n\n → </p><p> (단락 나누기)
  const lines = text.split('\n\n');
  return lines.map(p => '<p>' + p.replace(/\n/g, '<br>') + '</p>').join('');
}

// [2-1] 시간표 데이터 (API에서 로드)
// [3-1] 새 커리큘럼 적용
let SCHEDULE_DATA = {
  0: { name: '일요일', morning: '휴원', afternoon: '휴원' },
  1: { name: '월요일', morning: 'AI 기초 소양 (101호)', afternoon: '생성형 AI 활용 (102호)' },
  2: { name: '화요일', morning: '프롬프트 엔지니어링 (101호)', afternoon: '바이브 코딩 (102호)' },
  3: { name: '수요일', morning: 'AI 업무 자동화·ERP (101호)', afternoon: 'Private LLM ① (102호)' },
  4: { name: '목요일', morning: 'Private LLM ② (101호)', afternoon: 'AI 에이전트 (102호)' },
  5: { name: '금요일', morning: '에이전틱 AI (101호)', afternoon: 'AI 윤리와 보안·프로젝트 (102호)' },
  6: { name: '토요일', morning: '휴원', afternoon: '휴원' }
};

// [2-1] API에서 시간표 로드
async function loadScheduleData() {
  try {
    const response = await fetch('/api/docs');
    const docs = await response.json();

    if (docs['시간표']) {
      // [3-1] RAG_PLAN.md의 시간표 데이터를 파싱 (새 커리큘럼)
      SCHEDULE_DATA = {
        0: { name: '일요일', morning: '휴원', afternoon: '휴원' },
        1: { name: '월요일', morning: docs['시간표']['월요일']?.split('\n')[0] || 'AI 기초 소양 (101호)', afternoon: '생성형 AI 활용 (102호)' },
        2: { name: '화요일', morning: docs['시간표']['화요일']?.split('\n')[0] || '프롬프트 엔지니어링 (101호)', afternoon: '바이브 코딩 (102호)' },
        3: { name: '수요일', morning: docs['시간표']['수요일']?.split('\n')[0] || 'AI 업무 자동화·ERP (101호)', afternoon: 'Private LLM ① (102호)' },
        4: { name: '목요일', morning: docs['시간표']['목요일']?.split('\n')[0] || 'Private LLM ② (101호)', afternoon: 'AI 에이전트 (102호)' },
        5: { name: '금요일', morning: docs['시간표']['금요일']?.split('\n')[0] || '에이전틱 AI (101호)', afternoon: 'AI 윤리와 보안·프로젝트 (102호)' },
        6: { name: '토요일', morning: '휴원', afternoon: '휴원' }
      };

      // 오늘의 수업 다시 표시
      displayTodayClass();
    }
  } catch (error) {
    console.log('시간표 로드 실패 (로컬 데이터 사용):', error);
  }
}

// 초기화
document.addEventListener('DOMContentLoaded', function() {
  console.log('하나 AI 학원 웹사이트 로드됨');

  // 메뉴 초기화
  initializeMenu();

  // [3-6] 로그인 버튼
  const loginBtn = document.querySelector('.btn-login');
  if (loginBtn) {
    loginBtn.addEventListener('click', function() {
      alert('수업용 데모 사이트라 로그인이 없어요.\n신청은 가상 학번으로 해요.\n예: HANA-001');
    });
  }

  // [3-6] 관리자 화면 접근
  const adminLink = document.createElement('a');
  adminLink.href = 'admin.html';
  adminLink.style.position = 'fixed';
  adminLink.style.bottom = '20px';
  adminLink.style.left = '20px';
  adminLink.style.fontSize = '12px';
  adminLink.style.color = '#999';
  adminLink.style.textDecoration = 'none';
  adminLink.textContent = '⚙️ 관리자';
  document.body.appendChild(adminLink);

  // 시간표 데이터 로드 (API에서)
  loadScheduleData();

  // 슬라이더 초기화
  initializeSlider();

  // 오늘의 수업 표시
  displayTodayClass();

  // 탭 초기화
  initializeTabs();

  // 떠 있는 버튼 초기화
  initializeFloatingButtons();

  // 채팅 초기화
  initializeChat();

  // 모달 초기화
  initializeModals();

  // 데이터 로드
  loadPageData();
});

// 메뉴 기능
function initializeMenu() {
  const hamburger = document.getElementById('hamburger');
  const nav = document.getElementById('nav');
  const navItems = document.querySelectorAll('.nav-item');

  hamburger.addEventListener('click', function() {
    hamburger.classList.toggle('active');
    nav.classList.toggle('active');
  });

  navItems.forEach(item => {
    const title = item.querySelector('.nav-title');
    title.addEventListener('click', function(e) {
      if (window.innerWidth <= 768) {
        e.preventDefault();
        item.classList.toggle('open');
      }
    });
  });

  window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
      hamburger.classList.remove('active');
      nav.classList.remove('active');
      navItems.forEach(item => item.classList.remove('open'));
    }
  });

  document.addEventListener('click', function(e) {
    if (window.innerWidth <= 768) {
      if (!e.target.closest('header')) {
        hamburger.classList.remove('active');
        nav.classList.remove('active');
        navItems.forEach(item => item.classList.remove('open'));
      }
    }
  });
}

// [2-1] 슬라이더 기능
function initializeSlider() {
  const slider = document.getElementById('slider');
  const prevBtn = document.getElementById('sliderPrev');
  const nextBtn = document.getElementById('sliderNext');
  const pauseBtn = document.getElementById('sliderPause');
  const currentSlideSpan = document.getElementById('currentSlide');

  let currentSlide = 1;
  let totalSlides = 3;
  let isPlaying = true;
  let autoPlayInterval;

  function updateSlider() {
    const offset = (currentSlide - 1) * -100;
    slider.style.transform = `translateX(${offset}%)`;
    currentSlideSpan.textContent = currentSlide;
  }

  function nextSlide() {
    if (currentSlide < totalSlides) {
      currentSlide++;
    } else {
      currentSlide = 1;
    }
    updateSlider();
  }

  function prevSlide() {
    if (currentSlide > 1) {
      currentSlide--;
    } else {
      currentSlide = totalSlides;
    }
    updateSlider();
  }

  function startAutoPlay() {
    if (isPlaying) {
      autoPlayInterval = setInterval(nextSlide, 5000);
    }
  }

  function stopAutoPlay() {
    clearInterval(autoPlayInterval);
  }

  // 버튼 이벤트
  prevBtn.addEventListener('click', function() {
    prevSlide();
    stopAutoPlay();
    startAutoPlay();
  });

  nextBtn.addEventListener('click', function() {
    nextSlide();
    stopAutoPlay();
    startAutoPlay();
  });

  pauseBtn.addEventListener('click', function() {
    isPlaying = !isPlaying;
    pauseBtn.textContent = isPlaying ? '⏸ 일시정지' : '▶ 재생';
    pauseBtn.classList.toggle('playing');

    if (isPlaying) {
      startAutoPlay();
    } else {
      stopAutoPlay();
    }
  });

  // 초기 설정
  updateSlider();
  startAutoPlay();
}

// [2-1] 오늘의 수업 표시
function displayTodayClass() {
  const today = new Date().getDay();
  const todayClassDiv = document.getElementById('todayClass');
  const todayData = SCHEDULE_DATA[today];

  if (today === 0 || today === 6) {
    todayClassDiv.innerHTML = '<p style="color: var(--color-text-light); font-style: italic;">오늘은 휴원입니다</p>';
  } else {
    todayClassDiv.innerHTML = `
      <div class="today-class-item">
        <div class="today-class-time">오전 09:30 ~ 12:30</div>
        <div class="today-class-name">${todayData.morning}</div>
      </div>
      <div class="today-class-item">
        <div class="today-class-time">오후 14:00 ~ 17:00</div>
        <div class="today-class-name">${todayData.afternoon}</div>
      </div>
    `;
  }
}

// [2-1] 탭 기능
function initializeTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      const tabName = this.dataset.tab;

      // 모든 버튼과 콘텐츠에서 active 제거
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      // 클릭된 탭 활성화
      this.classList.add('active');
      document.getElementById(tabName).classList.add('active');
    });
  });
}

// [2-1] 떠 있는 버튼
function initializeFloatingButtons() {
  const floatHanabot = document.getElementById('floatHanabot');
  const floatConsult = document.getElementById('floatConsult');
  const floatFaq = document.getElementById('floatFaq');
  const floatTop = document.getElementById('floatTop');

  // [3-3] floatHanabot은 initializeChat에서 처리

  if (floatConsult) {
    floatConsult.addEventListener('click', function() {
      window.location.href = 'page.html?id=상담신청';
    });
  }

  if (floatFaq) {
    floatFaq.addEventListener('click', function() {
      document.querySelector('.tab-btn[data-tab="faq"]').click();
      document.getElementById('schedule-section').scrollIntoView({ behavior: 'smooth' });
    });
  }

  if (floatTop) {
    floatTop.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // 스크롤 시 떠 있는 버튼 표시/숨김
  window.addEventListener('scroll', function() {
    if (window.scrollY > 300) {
      document.querySelector('.floating-buttons').style.display = 'flex';
    } else {
      document.querySelector('.floating-buttons').style.display = 'flex';
    }
  });
}

// [2-1] 채팅 기능
function initializeChat() {
  const chatModal = document.getElementById('chatModal');
  const chatInput = document.getElementById('chatInput');
  const chatSend = document.getElementById('chatSend');
  const chatClose = document.getElementById('chatClose');
  const chatMessages = document.getElementById('chatMessages');

  // 채팅 열기/닫기
  function toggleChat() {
    chatModal.classList.toggle('active');
    if (chatModal.classList.contains('active')) {
      chatInput.focus();
    }
  }

  // [3-3] 메뉴바 "하나봇에게 묻기" 버튼 (.btn-hanabot)
  const btnHanabot = document.querySelector('.btn-hanabot');
  if (btnHanabot) {
    btnHanabot.addEventListener('click', toggleChat);
  }

  // 메뉴 링크 "하나봇에게 묻기"
  const hanabotButtons = document.querySelectorAll('a[href*="?id=하나봇"]');
  hanabotButtons.forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      toggleChat();
    });
  });

  // [3-3] 떠 있는 하나봇 버튼
  const floatHanabotBtn = document.getElementById('floatHanabot');
  if (floatHanabotBtn) {
    floatHanabotBtn.addEventListener('click', toggleChat);
  }

  // 닫기 버튼
  chatClose.addEventListener('click', toggleChat);

  // [3-3] 외부 클릭 시 닫기 (채팅 열기 버튼들은 제외)
  document.addEventListener('click', function(e) {
    const isChatArea = chatModal.contains(e.target);
    const isFloatingBtn = e.target.closest('.floating-buttons');
    const isHanabotBtn = e.target.closest('.btn-hanabot');
    const isHanabotLink = e.target.closest('a[href*="?id=하나봇"]');

    if (!isChatArea && !isFloatingBtn && !isHanabotBtn && !isHanabotLink) {
      chatModal.classList.remove('active');
    }
  });

  // [3-1] 메시지 전송 (한글 입력 문제 해결)
  let isSending = false;
  async function sendMessage() {
    // 중복 전송 방지
    if (isSending) return;

    const message = chatInput.value.trim();
    if (!message) return;

    isSending = true;

    // 사용자 메시지 표시
    const userDiv = document.createElement('div');
    userDiv.className = 'chat-message user';
    userDiv.innerHTML = `<div class="message-content">${escapeHtml(message)}</div>`;
    chatMessages.appendChild(userDiv);

    // 입력창 초기화
    chatInput.value = '';

    // 자동 스크롤
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // 서버에 메시지 전송
    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
      });

      const data = await response.json();
      const botReply = data.reply || '오류가 발생했습니다.';
      const sources = data.sources || [];

      // 봇 메시지 표시
      const botDiv = document.createElement('div');
      botDiv.className = 'chat-message bot';

      // [3-1] 근거 처리 (규정에 없는 경우 & 인사말 제외)
      let sourcesHtml = '';
      if (!botReply.includes('규정에 없는') && !botReply.includes('하나 AI 학원 규정을 물어보세요')) {
        // 근거 중복 제거 및 포맷팅
        const uniqueSources = [...new Set(sources)];

        if (uniqueSources.length > 0) {
          sourcesHtml = '<div class="chat-sources">';
          uniqueSources.forEach(src => {
            // "[# 제목 > ## 소제목]" 형식에서 제목과 소제목 추출
            const match = src.match(/\[# (.+?) > ## (.+?)\]/);
            if (match) {
              const title = match[1];
              const section = match[2];
              sourcesHtml += `<a href="page.html?id=${encodeURIComponent(title)}&section=${encodeURIComponent(section)}" class="chat-source-link">${title} > ${section}</a>`;
            }
          });
          sourcesHtml += '</div>';
        }
      }

      botDiv.innerHTML = `
        <div class="message-content">
          ${escapeHtml(botReply)}
          ${sourcesHtml}
        </div>
      `;
      chatMessages.appendChild(botDiv);

      // 자동 스크롤
      chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch (error) {
      console.error('채팅 오류:', error);
      const botDiv = document.createElement('div');
      botDiv.className = 'chat-message bot';
      botDiv.innerHTML = `<div class="message-content">오류가 발생했습니다.</div>`;
      chatMessages.appendChild(botDiv);
    } finally {
      isSending = false;
    }
  }

  // 전송 버튼
  chatSend.addEventListener('click', sendMessage);

  // [3-1] Enter 키로 전송 (한글 조합 중 제외, keydown 사용)
  chatInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.isComposing && e.keyCode !== 229) {
      e.preventDefault();
      sendMessage();
    }
  });

  // 모바일 감지 및 풀스크린 모드
  function updateChatForMobile() {
    if (window.innerWidth <= 480) {
      chatModal.classList.add('mobile-fullscreen');
    } else {
      chatModal.classList.remove('mobile-fullscreen');
    }
  }

  updateChatForMobile();
  window.addEventListener('resize', updateChatForMobile);
}

// XSS 방지 함수
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

// 모달 기능
function initializeModals() {
  // 상담 신청 모달 추가 예정
}

// 데이터 로드 (data/RAG_PLAN.md에서 읽기)
function loadPageData() {
  // 나중에 API를 통해 data/RAG_PLAN.md 콘텐츠 로드
}

// 스크롤 감지
window.addEventListener('scroll', function() {
  // 헤더 고정 등 스크롤 이벤트 추가 예정
});

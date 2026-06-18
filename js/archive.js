const moreGames = document.querySelector(".more-games");

if (moreGames) {
  const MONTHS = [
    "January", "February", "March",
    "April", "May", "June",
    "July", "August", "September",
    "October", "November", "December"
  ];
  const WEEK_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  const parseISODate = (value) => {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
  };

  const toISODate = (value) => {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const toMonthKey = (value) => {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    return `${year}-${month}`;
  };

  const shiftMonth = (value, delta) => new Date(value.getFullYear(), value.getMonth() + delta, 1);

  const getDateEntriesFromList = () => {
    const entries = [];
    const times = moreGames.querySelectorAll("time[datetime]");

    times.forEach((timeElement) => {
      const dateValue = timeElement.getAttribute("datetime");
      if (!/^\d{4}-\d{2}-\d{2}$/.test(dateValue)) {
        return;
      }
      entries.push(dateValue);
    });

    return entries;
  };

  const dataIsland = document.querySelector("#archive-data");
  let dataIslandDates = [];
  let dataIslandMinDate = null;
  let dataIslandMaxDate = null;
  let dataIslandThemes = {};

  if (dataIsland) {
    try {
      const data = JSON.parse(dataIsland.textContent || "{}");
      dataIslandDates = Array.isArray(data.availableDates)
        ? data.availableDates.filter((value) => /^\d{4}-\d{2}-\d{2}$/.test(value))
        : [];
      dataIslandMinDate = /^\d{4}-\d{2}-\d{2}$/.test(data.minDate || "") ? data.minDate : null;
      dataIslandMaxDate = /^\d{4}-\d{2}-\d{2}$/.test(data.maxDate || "") ? data.maxDate : null;
      dataIslandThemes = data.dateThemes && typeof data.dateThemes === "object" ? data.dateThemes : {};
    } catch {
      dataIslandDates = [];
      dataIslandMinDate = null;
      dataIslandMaxDate = null;
      dataIslandThemes = {};
    }
  }

  const fallbackDates = getDateEntriesFromList();
  const allDates = [...new Set((dataIslandDates.length ? dataIslandDates : fallbackDates).sort())];

  if (!allDates.length) {
    moreGames.innerHTML = "";
  } else {
    const availableDateSet = new Set(allDates);
    const monthWithGamesSet = new Set(allDates.map((dateValue) => dateValue.slice(0, 7)));

    const minDateValue = dataIslandMinDate || allDates[0];
    const maxDateValue = dataIslandMaxDate || allDates[allDates.length - 1];

    const minDate = parseISODate(minDateValue);
    const maxDate = parseISODate(maxDateValue);

    const today = new Date();
    const todayMonthStart = new Date(today.getFullYear(), today.getMonth(), 1);
    const maxMonthStart = new Date(maxDate.getFullYear(), maxDate.getMonth(), 1);
    const minMonthStart = new Date(minDate.getFullYear(), minDate.getMonth(), 1);

    let currentMonth = todayMonthStart;
    if (currentMonth > maxMonthStart) {
      currentMonth = maxMonthStart;
    }
    if (currentMonth < minMonthStart) {
      currentMonth = minMonthStart;
    }

    moreGames.className = "calendar-container";
    moreGames.innerHTML = `
      <div class="calendar-header">
        <button type="button" class="calendar-nav calendar-prev" aria-label="Show previous month" style="rotate:180deg;"></button>
        <h2 class="calendar-title"></h2>
        <button type="button" class="calendar-nav calendar-next" aria-label="Show next month"></button>
      </div>
      <div class="calendar" aria-label="Puzzle archive calendar">
        <div class="calendar-days calendar-grid"></div>
        <div class="calendar-dates calendar-grid"></div>
      </div>
    `;

    const previousButton = moreGames.querySelector(".calendar-prev");
    const nextButton = moreGames.querySelector(".calendar-next");
    const titleElement = moreGames.querySelector(".calendar-title");
    const dayNamesElement = moreGames.querySelector(".calendar-days");
    const datesElement = moreGames.querySelector(".calendar-dates");

    dayNamesElement.innerHTML = WEEK_DAYS.map((dayName) => `<div>${dayName}</div>`).join("");

    const updateNavState = () => {
      const previousMonth = shiftMonth(currentMonth, -1);
      const nextMonth = shiftMonth(currentMonth, 1);

      previousButton.disabled = !monthWithGamesSet.has(toMonthKey(previousMonth));
      nextButton.disabled = !monthWithGamesSet.has(toMonthKey(nextMonth));
    };

    const renderMonth = () => {
      const year = currentMonth.getFullYear();
      const month = currentMonth.getMonth();
      const monthName = MONTHS[month];

      titleElement.textContent = `${monthName} ${year}`;

      const firstDayOffset = new Date(year, month, 1).getDay();
      const daysInMonth = new Date(year, month + 1, 0).getDate();
      const totalCells = Math.ceil((firstDayOffset + daysInMonth) / 7) * 7;

      const cells = [];

      for (let index = 0; index < firstDayOffset; index += 1) {
        cells.push('<div class="calendar-date is-empty" aria-hidden="true"></div>');
      }

      for (let day = 1; day <= daysInMonth; day += 1) {
        const dayDate = new Date(year, month, day);
        const isoDate = toISODate(dayDate);

        if (availableDateSet.has(isoDate)) {
          const pathDate = isoDate.replace(/-/g, "/");
          const themeClass = typeof dataIslandThemes[isoDate] === "string" ? dataIslandThemes[isoDate].trim().toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "") : "";
          const themeClassName = themeClass ? ` ${themeClass}` : "";
          cells.push(
            `<a class="calendar-date is-available${themeClassName}" href="/games/${pathDate}" aria-label="Play puzzle for ${isoDate}">${day}</a>`
          );
        } else {
          cells.push(`<div class="calendar-date is-unavailable" aria-label="No puzzle on ${isoDate}">${day}</div>`);
        }
      }

      while (cells.length < totalCells) {
        cells.push('<div class="calendar-date is-empty" aria-hidden="true"></div>');
      }

      datesElement.innerHTML = cells.join("");
      updateNavState();
    };

    previousButton.addEventListener("click", () => {
      if (previousButton.disabled) {
        return;
      }
      currentMonth = shiftMonth(currentMonth, -1);
      renderMonth();
    });

    nextButton.addEventListener("click", () => {
      if (nextButton.disabled) {
        return;
      }
      currentMonth = shiftMonth(currentMonth, 1);
      renderMonth();
    });

    renderMonth();
  }
}
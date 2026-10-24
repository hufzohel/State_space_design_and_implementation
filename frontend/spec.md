<!-- The prompt used - look at this as the original spec requirements in case the md is wrong:
Create for me a frontend initial documents that depicts the requirement for it. There's no need to specify the tech and the folder structure since that can be left for the implementor to do. Now about the requirement:

1. It's html and css, following minimalist style, no need for anything fancy nor react nor anything, just plain simple html css. Since its usage is for visualization of the different puzzles and the different solver step by step. Minimalist style shouold make the task substantially easier since no need for complicated animation or lighting (most animations are on the puzzle's elements being interactable to show that it is changed and even these can be kept to minimalist style). The lighting also happens specifically when there are invalid configuration of the puzzle like pipes making loops (there should be lighting like highlighting the looped structure or something similar)&#x20;
2. The frontend should be able to let the user choose the puzzle (no need for a landing page, like a change of puzzle can be just different tab that shows different dashboards, like that of the google tab bar or edge side bar, stuff like that is sufficient, no need for a landing page).
3. The dashboard should have:
   1. the puzzle and its elements (interactable by humans so when it's not being solved by a solver a human can solve it), simply put, the UI of the game first.
   2. there's a table or something similar to that in chess.com that shows the moves the user or the solver has taken to solve the puzzle. (This sequence of move is navigatable when it's done). This should show the path taken by the solver be it a human or a solver.
   3. the puzzle remains in the state of solved (showing that it's solved, simply put winning and losing is shown on the puzzle itself) until the user click a button to generate a new puzzle. There are buttons to generate puzzles (like i just said but also a drop down list to choose the generator function if there are more than 1) and a drop down list and buttons to choose the solver (being human or different algorithm - if any - of the search algo, here there are at least 2 a heuristic and a dfs for each puzzle)
   4. There is an indicator of total steps taken and total time took (for generator only time to generate the puzzle is shown and no steps)&#x20;
4. The api created to connect to the backend should be simple too, so for example, there are a lot of stuffs that require the backend, like for example checking if a state of the puzzle is valid or not and choosing solver or choosing generator (i dont know for sure if all this needs backend). Hence the need for a simple api hook is obvious.

The rest of the things can be determined by the implementor, where the different UI element should be and all that. Remember just create a simple initial document for frontend, make sure it has the content mentioned above but dont make its too long and too complicated, it's just the specification of what should be in the frontend.
 -->

# Puzzle Search Visualizer — Frontend Requirements

## 1. Purpose and Design

Build a simple frontend for playing and visualizing the step-by-step solving of **Pipes** and **Minesweeper** puzzles.

- Use plain HTML and CSS, with lightweight JavaScript for interactions.
- Follow a minimalist style with clear layouts, readable puzzle elements, and simple controls.
- Keep animations subtle and limited to meaningful changes, such as rotating a pipe or revealing a Minesweeper cell.
- Clearly highlight invalid configurations on the puzzle itself. For example, Pipes loops should be visually highlighted without elaborate effects.

## 2. Puzzle Navigation

- Provide persistent tabs or a compact sidebar to switch between Pipes and Minesweeper.
- Each selection should open its puzzle dashboard directly; no landing page is required.
- Each dashboard should contain the relevant puzzle board, controls, history, and statistics.

## 3. Puzzle Dashboard

### 3.1 Puzzle Board

- Display the puzzle and its individual elements clearly.
- Support human interaction when the Human solver is selected, such as rotating Pipes tiles or revealing and flagging Minesweeper cells.
- Provide visual feedback for state changes, invalid configurations, and completion.
- Keep the final solved or lost state visible until the user generates a new puzzle. Do not automatically reset the board.

### 3.2 Move History

- Display an ordered list of actions taken by the human or algorithmic solver, similar to a chess move history.
- Allow users to navigate backward and forward through completed actions or select a particular step.
- Update the board to reflect the selected historical state.
- Keep the board, move history, and selected step synchronized.

### 3.3 Puzzle Generation and Solver Controls

- Provide a **Generate New Puzzle** button.
- If multiple generators are available, allow users to select one from a dropdown.
- Provide a solver dropdown containing Human and all available search algorithms.
- Each puzzle must offer at least one DFS solver and one heuristic-based solver.
- Provide a control to start algorithmic solving, with simple step-by-step playback and pause controls where appropriate.
- Selecting a different solver must not silently reset the current puzzle. Generating a new puzzle starts a new run.

### 3.4 Statistics

- Display total steps/actions and elapsed solving time for human and algorithmic runs.
- For puzzle generation, display generation time only; step count is not applicable.
- Clearly distinguish generation time from solving time and use consistent step-counting rules where practical.

## 4. Backend/API Integration

Keep frontend-to-backend communication simple and consistent. Provide a shared API helper or hook to avoid duplicating request-handling logic across UI elements.

The interface may need to request the following operations:

- List available puzzles, generators, and solvers.
- Generate a puzzle using the selected generator.
- Start a solver and retrieve its action sequence and statistics.
- Retrieve step-by-step progress or the completed solution sequence.
- Validate a puzzle state when validation cannot be determined reliably on the frontend.

Use the backend for search, generation, and authoritative puzzle-rule validation where appropriate. Simple visual interactions may be handled on the frontend, provided that state validity remains consistent.

The implementor may decide the exact API endpoints and which operations belong on the frontend or backend.

## 5. General Behavior

- Display loading, success, failure, invalid-state, and terminal-state feedback clearly but unobtrusively.
- Prevent conflicting actions during generation or solving, or define predictable behavior for them.
- Keep the puzzle board, history, selected step, terminal status, and statistics synchronized.
- Keep the interface easy to extend when additional generators or solvers are introduced.

## 6. Scope

This document specifies the required frontend behavior and capabilities, not implementation details. The implementor may determine the layout, placement of UI elements, API design, and internal organization, provided the requirements above are satisfied.
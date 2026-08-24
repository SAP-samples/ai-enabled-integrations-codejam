function parseExercise(full, first, creds) {
  console.log(`Found: ${full}`);
    const exerciseCode = first;
      // Step 3: Find the exercise in the array
      const exercise = creds.exerciseList.find(ex => ex.code === exerciseCode);
      // Step 4: Check if the exercise is completed
      if (exercise) {
        if (exercise.completed === true) {
          // Add green tick emoji if completed
          return `
> [!TIP|icon:fa-solid fa-check|label:Exercise completed]
> You have completed the exercise and we have verified it.
>`;
        } else if (exercise.inProcess === true) {
          // Add green tick emoji if completed
          return `
> [!TIP|icon:fa-solid fa-hourglass|label:Exercise submitted]
> We are reviewing your submission!.
>`;
        } else {
          // Add not completed emoji if not completed
          return `
> [!NOTE|icon:fa-solid fa-camera|label:Attach the screenshot]
> 
>  <form id="submit-form" class="submitForm">
>  <input type="hidden" name="workshop_ID" value="${creds.workshopID}">
>  <input type="hidden" name="exercise_ID" value="${exercise.ID}">
>  <input type="hidden" name="participant_ID" value="${creds.participantUUID}">
>    <label for="picture"></label>
>    <input type="file" id="picture" name="picture" accept="image/*" required multiple><br><br>
>    <textarea id="comment" name="comment" rows="4" cols="30" placeholder="Add your comment here..." required></textarea><br><br>
>    <button type="submit">Submit</button>
>  </form>
>`;
        }
      } else {
        return `
> [!WARNING|label:Exercise code not found]
> Contact the trainer.
>`;
      }
    }
const form	= document.getElementById("form");

form.addEventListener("submit", submitForm);

function submitForm(e)
{
	e.preventDefault();

	const audio		= document.getElementById("audio");
	const formData	= new FormData();

	for (let i = 0; i < audio.files.length; i++)
	{
		formData.append("audio", audio.files[i]);
	}

	fetch("http://localhost:3000/upload",
	{
		method:	"POST",
		body:	formData,
		headers:
		{
			"Content-Type":	"multipart/form-data"
		}
	})
	.then((res) => console.log(res))
	.catch((err) => ("Error occurred: ", err));
}
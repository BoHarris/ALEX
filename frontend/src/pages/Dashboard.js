import { Tabs, TabList, Tab, TabPanels, TabPanel } from "../components/Tabs";
import { useRedactedFiles } from "../hooks/useRedacted_files";
import { useCurrentUser } from "../hooks/useLoadUser";
import AnimatedLandingHeader from "../components/AnimatedLandingHeader";
import Upload from "./Upload";
function Dashboard() {
  const { user, loading: uL, error: uE } = useCurrentUser();
  const { files, loading: fL, fE } = useRedactedFiles();
  const backendURL = process.env.REACT_APP_BACKEND_URL;

  //loading hooks
  if (uL || fL) return <p>Loading... </p>;

  //error hook
  if (uE) return <p>Error: {uE.message}</p>;
  if (fE) return <p>Error: {fE.message}</p>;

  //check for missing data
  if (!files.length) return <p>No redacted files found</p>;
  if (!user) return <p>No user found</p>;

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-4xl font-bold mb-4">Hello, User {user.name}</h1>
      <AnimatedLandingHeader />
      <Tabs defaultValue="files">
        <TabList>
          <Tab value="files">Redacted Files</Tab>
          <Tab value="info">Your Info</Tab>
          <Tab value="upload">Upload</Tab>
        </TabList>

        <TabPanels>
          <TabPanel value="files">
            <ul className="space-y-2">
              {files.map((name) => (
                <li
                  key={name}
                  className="flex justify-between p-4 border rounded-lg"
                >
                  <span className="truncate">{name}</span>
                  <a
                    href={`${backendURL}/download/${name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Download
                  </a>
                </li>
              ))}
            </ul>
          </TabPanel>

          <TabPanel value="info">
            <p>
              Device token:{" "}
              <code className="break-all">{user.device_token}</code>
            </p>

            {/* add more user related details here*/}
          </TabPanel>
          <TabPanel value="upload">
            <Upload />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>
  );
}

export default Dashboard;

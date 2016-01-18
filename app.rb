require 'sinatra'
require 'json'
require 'sqlite3'
require 'csv'
db_handler = SQLite3::Database.new("ess2.db")

get '/room/:id' do
  # return web page
end

get '/schedule/:id' do
  data = IO.read("schedule_#{params[:id]}.json")
  print JSON.parse(data)['schedule'].to_json
  JSON.parse(data)['schedule'].to_json
end

get '/statistics/:id' do
  data = IO.read("schedule_#{params[:id]}.json")
    print 'start'
  res = db_handler.execute "select * from stats where id='#{params[:id]}'  and time % 900 < 60 and time>strftime('%s','now','-24 hours') order by time asc;"
  print 'done'
  csv_str = CSV.generate do |csv|
  	res.each do |ent|
  		csv << ent
  	end
  end
  print csv_str
  csv_str
end

def validateScheduleJson(schedule_json)
	schedule_json.each_with_index do |val, index|
		if index == 0
			last_element = schedule_json[-1]
			if last_element['end_time'] != val['start_time']
				return false, index
			end
		end
			prev_element = schedule_json[index-1]
			if prev_element['end_time'] != val['start_time']
				return false, index
			end
	end
	return true, 0
end

post '/schedule/:id' do
    request.body.rewind
    data = request.body.read
    p data
    s = 200
    result, index = validateScheduleJson(JSON.parse(data))
    if result == false
    	s = 422
    else
        sch = JSON.parse(data)
        new_sch = {'schedule' => sch}

	    f = File.new("schedule_#{params[:id]}.json",  "w+")
	    f.write(JSON.generate(new_sch))
	    f.close()
    end
    status s
    (index+1).to_s
end

get '/status/:id' do
  data = IO.read("status_#{params[:id]}.json")
  data
end

get '/name/:id' do
  data = IO.read("config_#{params[:id]}.json")
  data
end

get '/' do
	send_file 'public/index.html'
end

# shortcut for POST on /customers
post '/customers' do
  status, headers, body = call env.merge("PATH_INFO" => '/customers/')
  [status, headers, body.map(&:upcase)]
end
